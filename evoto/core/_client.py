"""
Evoto Plugin SDK - internal ``Client`` class backing the top-level ``evoto`` façade.

Plugin authors should ``import evoto`` and use the module-level helpers
(``evoto.task``, ``evoto.connect``, ``evoto.run``, ``evoto.on``,
``evoto.shutdown``, ...) plus the ``evoto.host`` low-level handle. This
module documents the underlying implementation only.

1) Hosted plugin, no GUI (blocking)::

    import evoto

    @evoto.task
    def hello(name: str) -> str:
        return f"Hello, {name}!"

    evoto.run()

2) Hosted plugin with GUI (non-blocking, you own the event loop)::

    import evoto

    @evoto.task
    def hello(name: str) -> str:
        return f"Hello, {name}!"

    evoto.connect()  # returns immediately
    app = QApplication(sys.argv)
    window = MyWindow()
    evoto.on_shutdown(window.close)
    window.show()
    app.exec_()
    evoto.shutdown()

3) External process that connects to a running host::

    import evoto

    @evoto.task
    def process(data: str) -> str:
        return data.upper()

    evoto.run()  # discovers listening host

    # With GUI:
    if evoto.host.discover_host():
        evoto.connect()
        ...
"""

import os
import sys
import logging
import atexit
from typing import Any, Callable

from .task import TaskRegistry
from .runtime import PluginRuntime
from .resource import file, image, FileResource, ImageResource
from .api_commands import HostCmd
from .api_fields import EventField, HostDocField, HostField, LogLevel, SilentActionValue
from .ipc_constants import (
    ENV_SOCKET_PATH,
    IS_WINDOWS,
    SOCKET_NAME as _IPC_SOCKET_NAME,
    default_socket_path,
    is_windows_pipe_path,
)
from ._internal.exceptions import ReplyStatus, SocketConnectionError

logger = logging.getLogger(__name__)


class Client:
    """
    Internal SDK client backing the :mod:`evoto` façade.

    Users never construct this directly - they ``import evoto`` and call
    :func:`evoto.connect` / :func:`evoto.run` / :func:`evoto.task` / ... which
    are thin passthroughs onto the module-level :data:`_instance` below.

    - :meth:`run` blocks: best for headless workers until host shutdown.
    - :meth:`connect` is non-blocking: pair with Qt/Tk/etc.; SDK reads the
      socket on a background thread.
    """

    def __init__(self):
        self._task_registry = TaskRegistry()
        self._runtime: PluginRuntime | None = None
        self._atexit_registered: bool = False

    @property
    def task(self):
        """
        Task decorator.

        Usage::

            @evoto.task
            def my_task(x: int) -> int:
                return x * 2

            @evoto.task(name="custom.name")
            def another_task(x):
                return x
        """
        return self._task_registry.register

    # --- Host discovery ---

    # Default production-prefixed name; sourced from :mod:`ipc_constants`.
    # ``DEFAULT_SOCKET_PATH`` is platform-correct:
    #   - Windows -> ``\\.\pipe\pro_evoto_plugin_host`` (named pipe)
    #   - POSIX   -> ``$TMPDIR/pro_evoto_plugin_host`` (Unix Domain Socket)
    SOCKET_NAME = _IPC_SOCKET_NAME
    DEFAULT_SOCKET_PATH = default_socket_path()

    @staticmethod
    def _host_endpoint_exists(path: str) -> bool:
        r"""Cheap probe: does the host currently accept connections at ``path``?

        - **Windows named pipe**: ``os.path.exists`` is special-cased on
          Windows to also walk the pipe namespace, so
          ``os.path.exists(r"\\.\pipe\<name>")`` returns True iff the
          pipe is listening. We keep a short ``CreateFile``-based
          fallback for safety in case that behaviour changes in a
          future Windows build.
        - **POSIX**: the UDS rendezvous is a real filesystem entry.
        """
        if not path:
            return False
        if IS_WINDOWS or is_windows_pipe_path(path):
            try:
                if os.path.exists(path):
                    return True
            except OSError:
                pass
            # Fallback: try to open the pipe read-only very briefly.
            try:
                from ._internal.win_pipe import WinPipeClient

                probe = WinPipeClient()
                probe.connect(path, timeout=0.1)
                probe.close()
                return True
            except Exception:
                return False
        return os.path.exists(path)

    @staticmethod
    def discover_host() -> str | None:
        r"""
        Return host socket path if the listener exists.

        Order:
        1. ``EVOTO_PLUGIN_SOCKET`` env override
        2. Platform default:
           - Windows -> ``\\.\pipe\pro_evoto_plugin_host`` (named pipe)
           - POSIX   -> ``$TMPDIR/pro_evoto_plugin_host``

        For non-production builds (``pro_pre`` / ``test`` / ``dev``)
        pass an explicit path, set ``EVOTO_PLUGIN_SOCKET``, or use
        ``demo/shared/env_config.resolve_socket_path()``.

        Returns:
            Path / pipe name, or None if the endpoint is absent.
        """
        env_path = os.environ.get(ENV_SOCKET_PATH)
        if env_path:
            return env_path

        if Client._host_endpoint_exists(Client.DEFAULT_SOCKET_PATH):
            return Client.DEFAULT_SOCKET_PATH
        return None

    @staticmethod
    def is_host_available() -> bool:
        """True if ``discover_host()`` finds a path."""
        return Client.discover_host() is not None

    @staticmethod
    def wait_for_host(timeout: float = 30.0, poll_interval: float = 1.0) -> str | None:
        """
        Poll until the host socket appears.

        Args:
            timeout: seconds
            poll_interval: seconds between tries

        Returns:
            Socket path, or None on timeout.
        """
        import time
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            path = Client.discover_host()
            if path:
                return path
            time.sleep(poll_interval)
        return None

    # --- Connection & lifecycle ---

    def connect(self, socket_path: str | None = None, timeout: float = 10.0) -> None:
        """
        Connect without blocking the UI thread.

        Socket resolution order matches :meth:`_resolve_socket_path`.
        Returns only after the runtime completes the mandatory
        ``plugin.hello`` handshake.

        Args:
            socket_path: Optional socket or pipe path. Omit to discover the
                running host automatically.
            timeout: Maximum seconds to wait for connection and handshake.

        Raises:
            SocketConnectionError, IncompatibleVersionError
        """
        socket_path = self._resolve_socket_path(socket_path)
        logger.info(f"Connecting to Host at {socket_path}...")

        self._ensure_runtime()
        self._runtime.connect(socket_path, timeout)

        if not self._atexit_registered:
            atexit.register(self.shutdown)
            self._atexit_registered = True

        logger.info("Connected to Host (non-blocking mode)")

    def run(self, socket_path: str | None = None) -> None:
        """
        Blocking mode: connect then wait for shutdown / disconnect / signals.

        ``socket_path`` defaults via the same rules as :meth:`connect`.

        Args:
            socket_path: Optional socket or pipe path. Omit to discover the
                running host automatically.
        """
        socket_path = self._resolve_socket_path(socket_path)
        logger.info(f"Starting Evoto SDK client with socket: {socket_path}")

        self._ensure_runtime()

        try:
            self._runtime.connect(socket_path)
            self._runtime.run()
        except Exception as e:
            logger.error(f"Evoto SDK runtime error: {e}", exc_info=True)
            sys.exit(1)

    def disconnect(self) -> None:
        """Close the connection without full shutdown.

        Event subscriptions and registered tasks are preserved.
        Call :meth:`connect` or :meth:`reconnect` afterwards to resume.
        """
        if self._runtime:
            self._runtime.disconnect()

    def reconnect(self, socket_path: str | None = None, timeout: float = 10.0) -> None:
        """Disconnect (if connected) then establish a fresh connection.

        Args:
            socket_path: Explicit socket path; defaults via the same
                resolution as :meth:`connect`.
            timeout: Connection timeout in seconds.
        """
        socket_path = self._resolve_socket_path(socket_path)
        self._ensure_runtime()
        self._runtime.connect(socket_path, timeout)
        logger.info("Reconnected to Host")

    def shutdown(self) -> None:
        """Tear down transport; call explicitly in GUI mode."""
        if self._runtime:
            self._runtime.shutdown()

    def on_shutdown(self, callback: Callable[[], None]) -> None:
        """
        Register hook for host shutdown / disconnect / signals.

        May run off the GUI thread-marshal UI work via Qt signals, ``QTimer``, etc.

        Args:
            callback: Zero-argument function called when the SDK shuts down
                because the host disconnected, the process is exiting, or
                :meth:`shutdown` was called.
        """
        self._ensure_runtime()
        self._runtime.add_shutdown_callback(callback)

    @property
    def is_connected(self) -> bool:
        """True if the transport is connected."""
        if self._runtime and self._runtime.socket_client:
            return self._runtime.socket_client.is_connected
        return False

    # --- Host RPC ---

    def call(
        self,
        method: str,
        params: dict[str, Any],
        timeout: float = 30.0,
        binary_data: bytes = None
    ) -> Any:
        """Blocking JSON-RPC call to host."""
        self._check_connected()
        return self._runtime.api_client.call(method, params, timeout, binary_data=binary_data)

    def call_async(
        self,
        method: str,
        params: dict[str, Any],
        callback: Callable[[Any, ReplyStatus], None],
        timeout: float = 30.0,
        binary_data: bytes = None
    ) -> str:
        """
        Async RPC; ``callback(result, status)`` fires on completion.

        Returns:
            request id (pass to :meth:`cancel_request`).
        """
        self._check_connected()
        return self._runtime.api_client.call_with_callback(
            method, params, callback, timeout, binary_data=binary_data
        )

    def cancel_request(self, request_id: str) -> bool:
        """Cancel a pending async request by id."""
        if not self._runtime or not self._runtime.api_client:
            return False
        return self._runtime.api_client.cancel_request(request_id)

    # --- API Discovery ---

    def discover(
        self,
        command: str | None = None,
        domain: str | None = None,
        timeout: float = 10.0,
    ) -> dict:
        """Query host API schema at runtime.

        Similar to ``dws schema`` - returns structured param/return
        definitions for all (or filtered) registered commands.

        Args:
            command: Exact command name filter (e.g. ``"project.create"``).
            domain: Domain prefix filter (e.g. ``"export"``).
            timeout: RPC timeout in seconds.

        Returns:
            Schema dict with ``app``, ``version``, ``api_version``,
            and ``commands`` (array of command schema objects including
            ``params``, ``returns``, ``events``).
        """
        params: dict = {}
        if command:
            params[HostDocField.COMMAND] = command
        if domain:
            params[HostDocField.DOMAIN] = domain
        return self.call(HostCmd.API_DOC, params, timeout=timeout)

    # --- Host lifecycle ---

    def quit_host(self, relaunch: bool = False, timeout: float = 5.0) -> dict:
        """Ask the Evoto host to shut itself down (``host.quit``).

        The host flushes the reply back to us first, then invokes
        ``Application::forceQuit(relaunch)`` on the next event-loop tick,
        so the returned dict is effectively an acknowledgement - the IPC
        channel will drop shortly after. Works in both normal UI mode and
        ``-silent`` background mode.

        Args:
            relaunch: When True the host relaunches itself after quitting.
            timeout: RPC timeout; the host typically replies within a few ms.

        Returns:
            ``{"accepted": True, "relaunch": bool}``.

        Example::

            evoto.connect()
            evoto.host.quit()              # close
            evoto.host.quit(relaunch=True) # restart
        """
        payload = {HostField.RELAUNCH: bool(relaunch)}
        return self.call(HostCmd.QUIT, payload, timeout=timeout)

    def configure_silent_timeout(
        self,
        timeout_seconds: int | None = None,
        action: str | None = None,
        *,
        timeout: float = 5.0,
    ) -> dict:
        """Configure the host's silent-mode auto-exit watcher (``host.silentTimeout``).

        When Evoto is launched with ``-silent``, a background watcher
        fires an action after ``timeout_seconds`` of having no plugin
        connected. The default is **300 s** with **action=quit**, so a
        host that no plugin ever attaches to will just exit.

        Call this method from a plugin to adjust either dimension:

        * ``timeout_seconds`` - integer, seconds; pass ``<= 0`` to
          disable the auto-exit entirely and let the host stay silent
          indefinitely.
        * ``action`` - one of :class:`SilentActionValue`
          (``"quit"`` / ``"show"``). ``"show"`` flips the host out of
          silent mode and shows the main window when the timer fires.

        Unspecified parameters keep their current value.

        Args:
            timeout_seconds: New timeout, or ``None`` to keep existing.
            action: ``"quit"`` / ``"show"``, or ``None`` to keep existing.
            timeout: RPC timeout (default 5 s).

        Returns:
            Snapshot after the update::

                {
                  "timeout_seconds": int,
                  "action": "quit" | "show",
                  "enabled": bool,                  # False when timeout <= 0
                  "connected_plugin_count": int,    # >0 means timer is paused
                }

        Raises:
            ApiError: with ``code=412`` when Evoto is not running in
                silent mode (the watcher only exists under ``-silent``).

        Example::

            # Keep the host alive forever (useful for a daemon plugin)
            evoto.host.configure_silent_timeout(timeout_seconds=0)

            # Instead of quitting, show the UI if no plugin attaches in 10 min
            evoto.host.configure_silent_timeout(600, "show")
        """
        payload: dict[str, Any] = {}
        if timeout_seconds is not None:
            payload[HostField.TIMEOUT_SECONDS] = int(timeout_seconds)
        if action is not None:
            action_str = str(action).lower()
            if action_str not in (SilentActionValue.QUIT, SilentActionValue.SHOW):
                raise ValueError(
                    f"action must be 'quit' or 'show', got {action!r}"
                )
            payload[HostField.ACTION] = action_str
        return self.call(HostCmd.SILENT_TIMEOUT, payload, timeout=timeout)

    # --- Host events ---

    def on(self, event_name: str, callback: Callable) -> None:
        """Subscribe to a host event. ``callback(data: dict)`` fires once per event.

        **Where does my callback run?**
            On the SDK's dedicated ``evoto-event`` thread (single worker,
            FIFO). NOT on the socket receiver thread, NOT on any GUI main
            thread. A slow callback therefore cannot stall host pings or
            RPC responses, but it WILL delay the next event for this plugin.

        **Safe things to do inside a callback**
            * Read/transform ``data``.
            * Call host RPCs synchronously - e.g.::

                  def on_created(data):
                      fresh = evoto.project.list()      # no deadlock
                      cache.replace(fresh)

            * Hand off to another thread: emit a Qt signal, schedule an
              asyncio task, push to a ``queue.Queue``.

        **Unsafe things (common pitfalls)**
            * Touching Qt/Tk widgets directly - it's a cross-thread
              operation and will crash or corrupt state. Marshal via a
              queued Qt signal::

                  class Win(QWidget):
                      changed = Signal(str, object)        # class-level

                      def __init__(self):
                          super().__init__()
                          self.changed.connect(self._apply)    # GUI thread
                          evoto.project.on_created(
                              lambda d: self.changed.emit("created", d)
                          )

            * Blocking on another event's delivery - callbacks all run on
              one thread, so ``event_a_done.wait()`` inside an event-B
              callback deadlocks itself.
            * Long compute / blocking I/O inline - every second spent here
              is a second the next event waits. Spawn a worker thread.

        Exceptions raised from the callback are logged and swallowed;
        they do not crash the plugin or drop the subscription.

        Args:
            event_name: Host event name, such as ``"export.completed"``.
            callback: Function called with the event payload dict.
        """
        self._ensure_runtime()
        is_new = self._runtime.add_event_listener(event_name, callback)
        if is_new and self.is_connected:
            try:
                self._runtime.api_client.call(HostCmd.SUBSCRIBE, {EventField.EVENTS: [event_name]})
            except Exception as e:
                logger.warning(f"Failed to subscribe to '{event_name}': {e}")

    def off(self, event_name: str, callback: Callable | None = None) -> None:
        """Unsubscribe from a host event.

        Args:
            event_name: Host event name to detach from.
            callback: Callback to remove. Omit to clear every handler for
                ``event_name`` registered by this client.
        """
        self._ensure_runtime()
        should_unsub = self._runtime.remove_event_listener(event_name, callback)
        if should_unsub and self.is_connected:
            try:
                self._runtime.api_client.call(HostCmd.UNSUBSCRIBE, {EventField.EVENTS: [event_name]})
            except Exception as e:
                logger.warning(f"Failed to unsubscribe from '{event_name}': {e}")

    # --- Resource helpers ---

    def file(self, path: str, mime_type: str | None = None) -> FileResource:
        """Build :class:`FileResource`."""
        return file(path, mime_type)

    def image(self, path: str, width: int | None = None, height: int | None = None) -> ImageResource:
        """Build :class:`ImageResource`."""
        return image(path, width, height)

    def log(self, message: str, level: str = LogLevel.INFO) -> None:
        """Forward a log message to the host when connected.

        Args:
            message: Log message text.
            level: Log level string, such as ``"info"``, ``"warning"`` or
                ``"error"``.
        """
        if self._runtime:
            self._runtime.log(level, message)
        else:
            getattr(logger, level, logger.info)(message)

    # --- Internals ---

    def _resolve_socket_path(self, socket_path: str | None) -> str:
        """Resolve socket path (see :meth:`connect`)."""
        if socket_path is not None:
            return socket_path

        # Hosted launch: argv[1] carries socket path
        if len(sys.argv) >= 2:
            return sys.argv[1]

        # External plugin: auto-discover
        discovered = self.discover_host()
        if discovered:
            logger.info(f"Auto-discovered Host socket: {discovered}")
            return discovered

        raise SocketConnectionError(
            f"Cannot find Host (expected socket: {Client.DEFAULT_SOCKET_PATH}). Options:\n"
            "  1. Pass socket_path to evoto.connect() / evoto.run()\n"
            "  2. Set env EVOTO_PLUGIN_SOCKET=<path>\n"
            "  3. Ensure Host is running (it listens on a fixed socket name)\n"
            "  4. Call evoto.host.wait_for_host() to wait for Host to start"
        )

    def _ensure_runtime(self) -> None:
        """Lazily construct :class:`PluginRuntime`."""
        if self._runtime is None:
            script_path = sys.argv[0] if sys.argv else None
            self._runtime = PluginRuntime(self._task_registry, script_path=script_path)

    def _check_connected(self) -> None:
        """Require API client to exist."""
        if not self._runtime or not self._runtime.api_client:
            raise RuntimeError(
                "Evoto SDK not connected. Call evoto.connect() or evoto.run() first."
            )


# Module-level singleton - consumed by :mod:`evoto` to build the façade.
_instance = Client()
