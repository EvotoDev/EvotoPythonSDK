"""Evoto Python SDK - unified package-level façade.

Everything a plugin author needs is attached to the :mod:`evoto` namespace::

    import evoto

    @evoto.task
    def hello(name: str) -> str:
        return f"Hello, {name}!"

    evoto.connect()                         # non-blocking (Qt-friendly)
    # or evoto.run()                        # blocking (headless workers)

    project = evoto.project.current()
    evoto.image.list(use_current_project=True)
    evoto.on("export.completed", lambda data: ...)
    evoto.log("Ready")
    evoto.shutdown()

The :data:`evoto.host` sub-namespace exposes low-level handles (raw JSON-RPC,
host-process discovery, host lifecycle) that everyday plugin code rarely
needs::

    evoto.host.call("image.list", {"project_id": 1})
    if evoto.host.is_connected:
        evoto.host.quit(relaunch=True)
"""

from .core._client import _instance as _client
from .core.resource import FileResource, ImageResource
from .core._internal.exceptions import ReplyStatus
from .core.version import SDK_VERSION
from typing import Callable

from .project import ProjectAPI as _ProjectAPI
from .image import ImageAPI as _ImageAPI, ImageInfo
from .preset import PresetAPI as _PresetAPI
from .export import ExportAPI as _ExportAPI
from .watcher import WatcherAPI as _WatcherAPI, ExportStatus, TimeUnit
from .user import UserAPI as _UserAPI, UserInfo
from .metadata import MetadataAPI as _MetadataAPI
from .library import LibraryAPI as _LibraryAPI
from .culling import CullingAPI as _CullingAPI
from .edit import EditAPI as _EditAPI
from .face import (
    FaceAPI as _FaceAPI,
    DetectedFace,
    FaceImageResult,
    FaceModelState,
    FaceTaskState,
)
from .export_options import (
    ExportOptions,
    PresetSuitId,
    FileFormat,
    QualityType,
    ScaleType,
    ScaleUnit,
    DpiUnit,
    SharpenType,
    SharpenAmount,
    ExistFormat,
    NamingFormat,
    WatermarkPosition,
)

__version__ = SDK_VERSION


# ---------------------------------------------------------------------------
# Domain APIs - what plugin code touches day-to-day.
# ---------------------------------------------------------------------------
project = _ProjectAPI(_client)
image = _ImageAPI(_client)
preset = _PresetAPI(_client)
export = _ExportAPI(_client)
watcher = _WatcherAPI(_client)
user = _UserAPI(_client)
metadata = _MetadataAPI(_client)
library = _LibraryAPI(_client)
culling = _CullingAPI(_client)
edit = _EditAPI(_client)
face = _FaceAPI(_client)


# ---------------------------------------------------------------------------
# Top-level lifecycle / tasks / events / logging conveniences.
# Thin wrappers keep the public API stable while giving documentation tools
# real functions to render instead of module attribute aliases.
# ---------------------------------------------------------------------------
def task(
    func: Callable | None = None,
    *,
    name: str | None = None,
    inline: bool = False,
) -> Callable:
    """Register a plugin task.

    Can be used as ``@evoto.task`` or ``@evoto.task(name="custom.name")``.

    Args:
        func: Function supplied automatically when used as ``@evoto.task``.
        name: Optional task name exposed to the host. Defaults to the
            function name.
        inline: Run the task on the SDK receiver thread when true. Use only
            for very fast, non-blocking callbacks.

    Returns:
        Decorator or the original function, matching normal decorator usage.
    """
    return _client.task(func, name=name, inline=inline)


def connect(socket_path: str | None = None, timeout: float = 10.0) -> None:
    """Connect to the host without blocking the UI thread.

    Args:
        socket_path: Internal override. Leave unset in normal plugins.
        timeout: Maximum seconds to wait for connection and handshake.
    """
    return _client.connect(socket_path, timeout)


def run(socket_path: str | None = None) -> None:
    """Connect to the host and block until shutdown.

    Args:
        socket_path: Internal override. Leave unset in normal plugins.
    """
    return _client.run(socket_path)


def disconnect() -> None:
    """Close the transport without clearing registered tasks or callbacks."""
    return _client.disconnect()


def shutdown() -> None:
    """Tear down the SDK transport and release runtime resources."""
    return _client.shutdown()


def on_shutdown(callback: Callable[[], None]) -> None:
    """Register a callback for host shutdown or SDK disconnect.

    Args:
        callback: Zero-argument function called when the host disconnects or
            the SDK shuts down.
    """
    return _client.on_shutdown(callback)


def on(event_name: str, callback: Callable[[dict], None]) -> None:
    """Subscribe to a host event.

    Args:
        event_name: Event name, such as ``"export.completed"``.
        callback: Function called with the event payload dict.
    """
    return _client.on(event_name, callback)


def off(event_name: str, callback: Callable | None = None) -> None:
    """Unsubscribe from a host event.

    Args:
        event_name: Event name to detach from.
        callback: Callback to remove. Omit to remove all callbacks for the
            event registered by this client.
    """
    return _client.off(event_name, callback)


def log(message: str, level: str = "info") -> None:
    """Forward a log message to the host when connected.

    Args:
        message: Log message text.
        level: Log level string, such as ``"info"``, ``"warning"`` or
            ``"error"``.
    """
    return _client.log(message, level)


# ---------------------------------------------------------------------------
# Low-level host handle (``evoto.host``) - raw RPC, introspection, process
# control. Prefer the domain APIs above for everyday work.
# ---------------------------------------------------------------------------
class _Host:
    """Low-level handle onto the connected Evoto host.

    Accessed via :data:`evoto.host`. Plugin authors should prefer the
    domain APIs (``evoto.project`` / ``evoto.image`` / ...) for everyday
    work; this namespace is for raw JSON-RPC, host-process discovery, and
    host lifecycle control.
    """

    sdk_version = SDK_VERSION

    # ---- Raw JSON-RPC ------------------------------------------------
    @staticmethod
    def call(
        method: str,
        params: dict,
        timeout: float = 30.0,
        binary_data: bytes | None = None,
    ) -> dict:
        """Blocking JSON-RPC call to the host.

        Args:
            method: Raw RPC command name, such as ``"image.list"``.
            params: JSON-compatible parameter dict for the command.
            timeout: Maximum seconds to wait for the reply.
            binary_data: Optional binary payload for commands that support it.

        Returns:
            Result payload returned by the host.
        """
        return _client.call(method, params, timeout, binary_data)

    @staticmethod
    def call_async(
        method: str,
        params: dict,
        callback: Callable,
        timeout: float = 30.0,
        binary_data: bytes | None = None,
    ) -> str:
        """Async JSON-RPC call.

        Args:
            method: Raw RPC command name.
            params: JSON-compatible parameter dict for the command.
            callback: Function called as ``callback(result, status)`` when
                the request finishes.
            timeout: Maximum seconds to wait before the request fails.
            binary_data: Optional binary payload for commands that support it.

        Returns:
            Request ID that can be passed to :meth:`cancel_request`.
        """
        return _client.call_async(method, params, callback, timeout, binary_data)

    @staticmethod
    def cancel_request(request_id: str) -> bool:
        """Cancel a pending async request by ID.

        Args:
            request_id: Request ID returned by :meth:`call_async`.

        Returns:
            True when a pending request was found and cancelled.
        """
        return _client.cancel_request(request_id)

    # ---- Internal API schema introspection ---------------------------
    @staticmethod
    def discover(
        command: str | None = None,
        domain: str | None = None,
        timeout: float = 10.0,
    ) -> dict:
        """Query host API schema at runtime.

        This is an internal diagnostics hook. Production hosts may disable
        this endpoint, so plugin code should not depend on it.

        Args:
            command: Exact command name to inspect, such as
                ``"project.create"``.
            domain: Domain prefix to inspect, such as ``"project"``.
            timeout: RPC timeout in seconds.

        Returns:
            Schema payload containing registered commands.
        """
        return _client.discover(command, domain, timeout)

    # ---- Host process discovery -------------------------------------
    @staticmethod
    def discover_host() -> str | None:
        """Return the host endpoint if the listener exists, else None."""
        return _client.discover_host()

    @staticmethod
    def wait_for_host(
        timeout: float = 30.0, poll_interval: float = 1.0
    ) -> str | None:
        """Poll until the host endpoint appears.

        Args:
            timeout: Maximum seconds to wait.
            poll_interval: Seconds between discovery attempts.

        Returns:
            Endpoint path when a host is found, otherwise ``None``.
        """
        return _client.wait_for_host(timeout, poll_interval)

    @staticmethod
    def is_available() -> bool:
        """True if the host endpoint can be discovered right now."""
        return _client.is_host_available()

    # ---- Connection control -----------------------------------------
    @staticmethod
    def reconnect(
        socket_path: str | None = None, timeout: float = 10.0
    ) -> None:
        """Disconnect, if connected, then establish a fresh connection.

        Args:
            socket_path: Internal override. Leave unset in normal plugins.
            timeout: Maximum seconds to wait for connection and handshake.
        """
        return _client.reconnect(socket_path, timeout)

    # ---- Host process control ---------------------------------------
    @staticmethod
    def quit(relaunch: bool = False, timeout: float = 5.0) -> dict:
        """Ask the host to shut itself down.

        Args:
            relaunch: Relaunch the host after shutdown when true.
            timeout: RPC timeout in seconds.

        Returns:
            Host acknowledgement payload.
        """
        return _client.quit_host(relaunch, timeout)

    @staticmethod
    def configure_silent_timeout(
        timeout_seconds: int | None = None,
        action: str | None = None,
        timeout: float = 5.0,
    ) -> dict:
        """Configure the silent-mode auto-exit watcher (``host.silentTimeout``).

        Evoto runs in the background when its executable is started with
        ``-silent``; only such a host has this watcher, so a normally
        launched host rejects the call with 412.

        By default the silent host quits once no plugin has been
        connected for the timeout window - it does not show the UI on
        its own. Pass ``action="show"`` to make it leave silent mode
        and show the main window instead. See
        :meth:`evoto.core._client.Client.configure_silent_timeout` for
        full semantics.

        Args:
            timeout_seconds: new timeout in seconds (``<= 0`` disables
                auto-exit); ``None`` keeps the current value.
            action: ``"quit"`` or ``"show"``; ``None`` keeps the current.
            timeout: RPC timeout in seconds.

        Returns:
            Host acknowledgement payload.
        """
        return _client.configure_silent_timeout(
            timeout_seconds=timeout_seconds,
            action=action,
            timeout=timeout,
        )

    # ---- Transport state --------------------------------------------
    @property
    def is_connected(self):
        """True if the transport is connected to the host."""
        return _client.is_connected


host = _Host()


__all__ = [
    "__version__",
    # --- Domain APIs ---
    "project",
    "image",
    "preset",
    "export",
    "watcher",
    "user",
    "metadata",
    "library",
    "culling",
    "edit",
    "face",
    # --- Lifecycle / tasks / events / logging ---
    "task",
    "connect",
    "run",
    "disconnect",
    "shutdown",
    "on_shutdown",
    "on",
    "off",
    "log",
    # --- Low-level host handle ---
    "host",
    # --- Exported dataclasses / helpers ---
    "ImageInfo",
    "UserInfo",
    "FaceModelState",
    "FaceTaskState",
    "DetectedFace",
    "FaceImageResult",
    "FileResource",
    "ImageResource",
    "ReplyStatus",
    # --- Export option enums ---
    "ExportOptions",
    "PresetSuitId",
    "FileFormat",
    "QualityType",
    "ScaleType",
    "ScaleUnit",
    "DpiUnit",
    "SharpenType",
    "SharpenAmount",
    "ExistFormat",
    "NamingFormat",
    "WatermarkPosition",
    # --- Watcher enums ---
    "ExportStatus",
    "TimeUnit",
]
