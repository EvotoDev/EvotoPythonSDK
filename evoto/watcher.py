"""Folder watching and export monitoring host RPC wrappers."""

from __future__ import annotations

from enum import Enum, IntEnum
from typing import Callable

from .core.api_commands import WatchCmd
from .core.api_fields import WatchField, Field


class ExportStatus(IntEnum):
    """Image export status flag used by :meth:`WatcherAPI.mark_exported`.

    ``UNEXPORTED`` marks images as pending export; ``EXPORTED`` marks them
    as already handled by the folder-watching workflow.
    """
    UNEXPORTED = 0
    EXPORTED = 1


class TimeUnit(str, Enum):
    """Timer interval unit for :meth:`WatcherAPI.start_export_monitor`."""
    SECONDS = "s"
    MINUTES = "m"


class WatchFilterType(str, Enum):
    """Allowed values for :meth:`WatcherAPI.start`'s ``filters`` argument."""
    RAW = "raw"
    JPG = "jpg"
    TIFF = "tiff"
    PNG = "png"


class WatcherAPI:
    """Start / stop / list folder watchers, receive file-added events,
    and manage the export monitor timer."""

    def __init__(self, client):
        self._client = client

    # ------------------------------------------------------------------
    # Folder watching
    # ------------------------------------------------------------------

    def start(
        self,
        paths: list[str],
        filters: list[WatchFilterType | str] | None = None,
        include_sub_dir: bool = False,
    ) -> dict:
        """Start watching folders for new files.

        Only one watcher is active at a time.  Calling ``start`` again
        replaces the previous watcher configuration.

        Args:
            paths: Directory paths to watch.
            filters: File type filters, e.g. :class:`WatchFilterType` members
                (``RAW`` / ``JPG`` / ``TIFF`` / ``PNG``) or their string values.
                ``None`` means all supported types.
            include_sub_dir: Watch subdirectories.

        Returns:
            ``{"watchId": "...", "paths": [...], "success": True}``
        """
        params = {
            WatchField.PATHS: paths,
            WatchField.INCLUDE_SUB_DIR: include_sub_dir,
        }
        if filters is not None:
            params[WatchField.FILTERS] = [
                f.value if isinstance(f, WatchFilterType) else f for f in filters
            ]
        return self._client.call(WatchCmd.START, params)

    def stop(self) -> dict:
        """Stop the current folder watcher.

        Returns:
            ``{"success": True}``
        """
        return self._client.call(WatchCmd.STOP, {})

    def list(self) -> list:
        """Query the current folder watcher status.

        Returns:
            List with 0 or 1 watcher info dicts.
        """
        result = self._client.call(WatchCmd.LIST, {})
        return result.get(WatchField.WATCHERS, [])

    def on_files_added(self, callback: Callable[[dict], None]) -> None:
        """Register a callback for new file detection events.

        The callback receives ``{"watchId": "...", "files": ["..."]}``

        Args:
            callback: Function called with the file-added event payload.
        """
        self._client.on(WatchCmd.FILES_ADDED, callback)

    def off_files_added(self, callback: Callable | None = None) -> None:
        """Unregister file-added callback.

        Args:
            callback: Callback to remove. Omit to remove all file-added
                callbacks registered by this client.
        """
        self._client.off(WatchCmd.FILES_ADDED, callback)

    # ------------------------------------------------------------------
    # Export monitor - timer-based unexported image detection
    # ------------------------------------------------------------------

    def start_export_monitor(
        self,
        project_id: int,
        interval: int = 30,
        unit: TimeUnit | str = TimeUnit.SECONDS,
    ) -> dict:
        """Add or update an export monitor for a project.

        Multiple projects can be monitored simultaneously. Each call
        adds a new project or updates the interval for an existing one.

        Args:
            project_id: Project to monitor.
            interval: Timer interval value. Must be positive.
            unit: ``TimeUnit.SECONDS`` or ``TimeUnit.MINUTES``.

        Returns:
            ``{"success": True, "project_id": int, "interval": N, "unit": "s", "total_monitors": N}``
        """
        return self._client.call(WatchCmd.EXPORT_MONITOR_START, {
            WatchField.PROJECT_ID: project_id,
            WatchField.INTERVAL: interval,
            WatchField.UNIT: unit,
        })

    def stop_export_monitor(self, project_id: int | None = None) -> dict:
        """Stop export monitor for a specific project, or all if omitted.

        Args:
            project_id: Project to stop monitoring; omit to stop all.

        Returns:
            ``{"success": True, "stopped_count": N}``
        """
        params: dict = {}
        if project_id is not None:
            params[WatchField.PROJECT_ID] = project_id
        return self._client.call(WatchCmd.EXPORT_MONITOR_STOP, params)

    def query_export_monitor(self) -> dict:
        """Query all active export monitor configurations.

        Returns:
            ``{"project_ids": [int, ...], "interval": int, "unit": "s" | "m", "total": int, "running": bool}``
        """
        return self._client.call(WatchCmd.EXPORT_MONITOR_QUERY, {})

    def on_unexported_found(self, callback: Callable[[dict], None]) -> None:
        """Register a callback for ``watch.unexported.found`` events.

        The callback receives
        ``{"project_id": int, "images": [...], "total": int}``.

        Each image contains ``id``, ``absolute_path``, ``filename``.

        **Runs on a background thread** - GUI callers must marshal to the
        main thread themselves.

        Args:
            callback: Function called with unexported-image payloads.
        """
        self._client.on(WatchCmd.UNEXPORTED_FOUND, callback)

    def off_unexported_found(self, callback: Callable | None = None) -> None:
        """Unregister unexported-found callback.

        Args:
            callback: Callback to remove. Omit to remove all unexported-found
                callbacks registered by this client.
        """
        self._client.off(WatchCmd.UNEXPORTED_FOUND, callback)

    # ------------------------------------------------------------------
    # One-shot unexported image queries
    # ------------------------------------------------------------------

    def list_unexported(self, project_id: int) -> list:
        """Return images with ``exportStatus == 0`` in the given project.

        Each item contains ``id``, ``absolute_path``, ``filename``.

        Args:
            project_id: Target project ID.

        Returns:
            List of image dicts.
        """
        result = self._client.call(
            WatchCmd.LIST_UNEXPORTED,
            {WatchField.PROJECT_ID: project_id},
        )
        return result.get(WatchField.IMAGES, [])

    def mark_exported(
        self,
        *,
        image_ids: list[int],
        export_status: ExportStatus | int = ExportStatus.EXPORTED,
    ) -> dict:
        """Batch-update the export status of images.

        Args:
            image_ids: Image ID integers.
            export_status: Target status, e.g. ``ExportStatus.EXPORTED``
                or ``ExportStatus.UNEXPORTED``.

        Returns:
            ``{"success": True, "updated_count": N}``
        """
        payload: dict = {
            WatchField.EXPORT_STATUS: export_status,
            WatchField.IMAGE_IDS: image_ids,
        }
        return self._client.call(WatchCmd.MARK_EXPORTED, payload)
