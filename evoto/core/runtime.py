"""Plugin runtime: lifecycle and IPC."""

import os
import sys
import json
import signal
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from ._internal.socket_client import SocketClient, BINARY_DATA_KEY
from ._internal.host_api_client import HostApiClient
from ._internal.json_rpc import JsonRpc
from ._internal.exceptions import IncompatibleVersionError, ApiError
from .task import TaskRegistry
from .resource import FileResource, ImageResource
from .version import SDK_VERSION, MIN_API_VERSION
from .api_commands import HostCmd, PluginCmd
from .api_fields import PluginField, VersionField, EventField, Field
from .ipc_constants import MANIFEST_FILENAME, ENV_AUTH_TOKEN, PluginManifestKey

logger = logging.getLogger(__name__)


def _detect_plugin_id(script_path: str | None = None) -> str:
    """
    Detect plugin_id:
    1. plugin.json next to the script
    2. plugin.json in parent directory (nested layout)
    3. empty string (host maps by process)
    """
    search_dirs = []

    if script_path:
        script_dir = os.path.dirname(os.path.abspath(script_path))
        search_dirs.append(script_dir)
        search_dirs.append(os.path.dirname(script_dir))

    # Also probe cwd
    search_dirs.append(os.getcwd())

    for d in search_dirs:
        manifest = os.path.join(d, MANIFEST_FILENAME)
        if os.path.isfile(manifest):
            try:
                with open(manifest, "r", encoding="utf-8") as f:
                    data = json.load(f)
                plugin_id = data.get(PluginManifestKey.ID, "")
                if plugin_id:
                    logger.debug(f"Detected plugin_id '{plugin_id}' from {manifest}")
                    return plugin_id
            except Exception as e:
                logger.warning(f"Failed to read {manifest}: {e}")

    return ""


#: Host -> plugin methods that must never be queued behind user tasks.
#: All are constant-time SDK-internal handlers:
#:   - ``plugin.ping`` - keepalive; queuing it behind a slow task risks
#:     the host marking us dead.
#:   - ``plugin.shutdown`` - must ACK quickly and deterministically so
#:     the socket stays open long enough to flush the response.
#:   - ``plugin.event`` - host fan-out; the inline handler only hands
#:     the payload off to a dedicated single-threaded executor and
#:     immediately ACKs, so a slow user callback can never stall the
#:     receiver thread or re-entrant RPCs.
_INLINE_BUILTINS = frozenset({
    PluginCmd.PING,
    PluginCmd.SHUTDOWN,
    PluginCmd.EVENT,
})


class PluginRuntime:
    """Owns socket, API client, and task/event wiring."""

    def __init__(self, task_registry: TaskRegistry, script_path: str | None = None):
        """
        Args:
            task_registry: tasks registered in this process
            script_path: entry script path for inferring plugin_id
        """
        self.task_registry = task_registry
        self.socket_client: SocketClient | None = None
        self.api_client: HostApiClient | None = None
        self._running = False
        self._shutdown_event = threading.Event()
        self._shutdown_callbacks: list = []

        self._plugin_id = _detect_plugin_id(script_path)
        # Auth token from env (set by host child process launcher; keep off argv)
        self._auth_token = os.environ.get(ENV_AUTH_TOKEN, "")
        # event_name -> list of callbacks. Guarded by :attr:`_subscription_lock`
        # against concurrent subscribe/unsubscribe (user thread) and
        # dispatch snapshot (``evoto-event`` thread).
        self._event_callbacks: dict[str, list] = {}
        self._subscription_lock = threading.Lock()
        self._user_disconnecting = False

        # Dedicated single-threaded executor for user event callbacks.
        # Eagerly created in :meth:`connect` (before any event could
        # arrive) and torn down in :meth:`shutdown`. The receive hot
        # path reads ``self._event_executor`` without taking any lock -
        # creation and teardown are the only writes, and both are
        # serialised against each other by :attr:`_event_executor_lock`.
        # Single worker preserves host -> plugin delivery order.
        self._event_executor: ThreadPoolExecutor | None = None
        self._event_executor_lock = threading.Lock()

    def connect(self, socket_path: str, timeout: float = 10.0) -> None:
        """Connect to host socket and immediately finish ``plugin.hello``.

        Safe to call when already connected - tears down old transport first.
        """
        if self.socket_client and self.socket_client.is_connected:
            self.disconnect()

        logger.info(f"Connecting to Host at {socket_path}...")

        self._shutdown_event.clear()
        self._user_disconnecting = False

        self.socket_client = SocketClient()
        self.socket_client.set_disconnect_callback(self._on_disconnected)
        self.socket_client.connect(socket_path, timeout)

        self.api_client = HostApiClient(self.socket_client)
        self.api_client.set_task_handler(
            self._handle_task_call,
            inline_predicate=self._is_inline_method,
        )

        # Start the event dispatch thread before the handshake so the
        # receive loop can submit events without a lock on every call.
        self._ensure_event_executor()

        self._handshake()
        self._sync_event_subscriptions()

        logger.info("Connected to Host")

    def _handshake(self) -> None:
        """Handshake and verify API version."""
        tasks = self.task_registry.list_tasks()
        try:
            result = self.api_client.call(PluginCmd.HELLO, {
                PluginField.PLUGIN_ID: self._plugin_id,
                PluginField.AUTH_TOKEN: self._auth_token,
                VersionField.SDK_VERSION: SDK_VERSION,
                VersionField.MIN_API_VERSION: MIN_API_VERSION,
                PluginField.TASKS: tasks
            })
        except ApiError as e:
            # The true handshake failure cause (auth / 409 conflict /
            # version mismatch / ...) lives in e.code + e.message. Log it
            # at ERROR so it's immediately visible to demos and support,
            # then re-raise as IncompatibleVersionError for callers that
            # already handle that type; keep the code in the message so
            # no information is lost on the way up.
            logger.error(
                f"Plugin hello rejected by host: code={e.code} message={e.message} "
                f"(plugin_id={self._plugin_id!r})"
            )
            raise IncompatibleVersionError(
                f"Host rejected handshake [{e.code}]: {e.message}"
            ) from e

        logger.debug(f"Handshake response: {result}")

        # The host (C++) is the single authoritative version gate: it validates
        # the SDK version during plugin.hello and rejects incompatible plugins
        # via the ApiError handled above. The SDK no longer re-rejects based on
        # the reported host API version; runtime calls surface clear errors if a
        # required host endpoint is unavailable.
        host_api_version = result.get(VersionField.API_VERSION, "1.0.0")
        logger.debug(f"Host API version: {host_api_version}")

        # After hello, stamp outgoing _meta for all RPCs
        self.api_client.set_meta_context({
            PluginField.PLUGIN_ID: self._plugin_id,
            VersionField.SDK_VERSION: SDK_VERSION,
        })
        logger.debug(f"Meta context set: plugin_id={self._plugin_id}, sdk_version={SDK_VERSION}")

    def _is_inline_method(self, method: str) -> bool:
        """Return True if ``method`` must run on the receiver thread.

        SDK built-ins in :data:`_INLINE_BUILTINS` are always inline.
        User tasks are inline only when registered with ``inline=True``.
        """
        if method in _INLINE_BUILTINS:
            return True
        if method.startswith(PluginCmd.TASK_PREFIX):
            task_name = method[len(PluginCmd.TASK_PREFIX):]
            return self.task_registry.is_inline(task_name)
        return False

    def _handle_task_call(self, method: str, params: dict[str, Any]) -> Any:
        """
        Handle host-invoked methods.

        Args:
            method: e.g. task.foo or plugin.shutdown
            params: JSON object parameters

        Returns:
            JSON-serializable dict (or wrapped scalars).
        """
        # Built-ins handled by SDK

        # Keepalive
        if method == PluginCmd.PING:
            return {PluginField.PONG: True}

        # Graceful shutdown from host
        if method == PluginCmd.SHUTDOWN:
            logger.info("Received shutdown request from Host")
            self._fire_shutdown_callbacks()
            self._shutdown_event.set()
            return {PluginField.ACKNOWLEDGED: True}

        # Host event delivery - offload to the dedicated event thread so
        # user callbacks never run on the socket receiver thread. Keeps
        # ping/response parsing responsive and makes it safe for a
        # callback to issue synchronous RPCs back to the host.
        #
        # ``self._event_executor`` is created eagerly in :meth:`connect`
        # before any event can arrive, so the lock-free read is safe:
        # the only time it is None is pre-connect or post-shutdown,
        # both of which fall through to inline dispatch.
        if method == PluginCmd.EVENT:
            event_name = params.get(EventField.EVENT, "")
            event_data = params.get(EventField.DATA, {})
            executor = self._event_executor
            if executor is not None:
                try:
                    executor.submit(self._dispatch_event, event_name, event_data)
                    return {PluginField.HANDLED: True}
                except RuntimeError:
                    # Executor shut down concurrently (e.g. during disconnect).
                    # Fall through to inline dispatch so the event is not lost.
                    logger.warning(
                        f"Event executor shut down; dispatching '{event_name}' inline"
                    )
            self._dispatch_event(event_name, event_data)
            return {PluginField.HANDLED: True}

        if method.startswith(PluginCmd.TASK_PREFIX):
            task_name = method[len(PluginCmd.TASK_PREFIX):]
        else:
            task_name = method

        logger.info(f"Executing task: {task_name} with params: {list(params.keys())}")

        result = self.task_registry.execute(task_name, params)

        # Convert resource handles to dicts
        if isinstance(result, (FileResource, ImageResource)):
            result = result.to_dict()

        # Host expects JSON object for result
        if not isinstance(result, dict):
            result = {Field.RESULT: result}

        return result

    # --- Event subscriptions ---

    def add_event_listener(self, event_name: str, callback) -> bool:
        """Return True if this is the first listener for event_name (host subscribe).

        The ``is_new`` decision and the append are held under a single
        lock so two threads subscribing to the same event can never
        both think they are the "first" (which would double-fire
        ``host.subscribe``).
        """
        with self._subscription_lock:
            is_new = event_name not in self._event_callbacks
            if is_new:
                self._event_callbacks[event_name] = []
            self._event_callbacks[event_name].append(callback)
        return is_new

    def remove_event_listener(self, event_name: str, callback=None) -> bool:
        """Return True if event_name has no listeners left (host unsubscribe)."""
        with self._subscription_lock:
            if event_name not in self._event_callbacks:
                return False
            if callback is None:
                del self._event_callbacks[event_name]
                return True
            try:
                self._event_callbacks[event_name].remove(callback)
            except ValueError:
                return False
            if not self._event_callbacks[event_name]:
                del self._event_callbacks[event_name]
                return True
            return False

    def _ensure_event_executor(self) -> ThreadPoolExecutor:
        """Idempotently start the event dispatch executor.

        Called from :meth:`connect` (main thread) before any event can
        be received, so the receive hot path can later read
        ``self._event_executor`` without taking any lock.
        """
        with self._event_executor_lock:
            if self._event_executor is None:
                self._event_executor = ThreadPoolExecutor(
                    max_workers=1,
                    thread_name_prefix="evoto-event",
                )
            return self._event_executor

    def _dispatch_event(self, event_name: str, data: dict) -> None:
        """Run registered callbacks for ``event_name``.

        Executes on the dedicated ``evoto-event`` thread (see
        :meth:`_ensure_event_executor`), NOT the socket receiver thread.

        A snapshot of the callback list is taken under
        :attr:`_subscription_lock` so concurrent subscribe/unsubscribe
        from other threads cannot skip or double-deliver an event.
        Callbacks themselves run OUTSIDE the lock, which means a
        callback may freely call :meth:`add_event_listener` /
        :meth:`remove_event_listener` (e.g. one-shot listeners that
        ``off`` themselves) without self-deadlocking.

        Note for GUI (Qt/Tk/...) plugins: callbacks still run off the
        GUI main thread, so any widget manipulation must be marshalled
        back - e.g. via ``Signal`` with a queued connection.
        """
        with self._subscription_lock:
            callbacks = list(self._event_callbacks.get(event_name, ()))
        for cb in callbacks:
            try:
                cb(data)
            except Exception as e:
                logger.error(f"Event callback error for '{event_name}': {e}")

    def _sync_event_subscriptions(self) -> None:
        """Replay pre-registered listeners to host.subscribe after connect."""
        with self._subscription_lock:
            events = list(self._event_callbacks.keys())
        if events and self.api_client:
            try:
                self.api_client.call(HostCmd.SUBSCRIBE, {EventField.EVENTS: events})
                logger.debug(f"Synced event subscriptions: {events}")
            except Exception as e:
                logger.warning(f"Failed to sync event subscriptions: {e}")

    # --- Shutdown hooks ---

    def add_shutdown_callback(self, callback: callable) -> None:
        """Register cleanup hook (e.g. close GUI window)."""
        self._shutdown_callbacks.append(callback)

    def _fire_shutdown_callbacks(self) -> None:
        """Invoke registered shutdown callbacks."""
        for cb in self._shutdown_callbacks:
            try:
                cb()
            except Exception as e:
                logger.error(f"Shutdown callback error: {e}")

    def _on_disconnected(self) -> None:
        """Invoked from receiver thread when socket drops."""
        if self._user_disconnecting:
            logger.info("User-initiated disconnect completed")
            return
        logger.warning("Connection to Host lost")
        self._fire_shutdown_callbacks()
        self._shutdown_event.set()

    def run(self) -> None:
        """Block until host shutdown or signal."""
        self._running = True

        # Forward signals to shutdown event
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        logger.info("Plugin is running. Press Ctrl+C to stop.")

        # Wait for shutdown
        try:
            self._shutdown_event.wait()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def _signal_handler(self, signum, frame):
        """POSIX signal handler."""
        logger.info(f"Received signal {signum}, shutting down...")
        self._shutdown_event.set()

    def disconnect(self) -> None:
        """Close transport without triggering shutdown callbacks.

        Event subscriptions and task registry are preserved so a subsequent
        :meth:`connect` can resume normal operation.
        """
        self._user_disconnecting = True

        if self.api_client:
            self.api_client.cancel_all()

        if self.socket_client:
            self.socket_client.disconnect()

        self.api_client = None
        self.socket_client = None
        self._user_disconnecting = False
        logger.info("Disconnected from Host (state preserved)")

    def shutdown(self) -> None:
        """Cancel pending calls and tear down transport."""
        self._running = False

        if self.api_client:
            self.api_client.cancel_all()

        if self.socket_client:
            self.socket_client.disconnect()

        # Release the event dispatch thread. In-flight callbacks keep
        # running to completion (wait=False), but no new work is
        # accepted - matches host_api_client's executor teardown.
        with self._event_executor_lock:
            if self._event_executor is not None:
                self._event_executor.shutdown(wait=False)
                self._event_executor = None

        logger.info("Plugin shutdown complete")

    def log(self, level: str, message: str) -> None:
        """Forward log line to host.log RPC."""
        if self.api_client:
            try:
                self.api_client.log(level, message)
            except Exception as e:
                logger.error(f"Failed to send log to host: {e}")

    def ping(self) -> bool:
        """Return True if host.ping succeeds."""
        if self.api_client:
            try:
                result = self.api_client.ping()
                return result.get(PluginField.PONG, False)
            except Exception:
                return False
        return False
