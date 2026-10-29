"""Export API wrappers for preset-based image export."""

import threading
import logging
from typing import Callable

from .core.api_commands import ExportCmd
from .core.api_fields import ExportField

logger = logging.getLogger(__name__)

_PRESET_PREPARATION_TIMEOUT = 120.0


def _format_export_failure(export_dir_id: int, payload: dict) -> str:
    """Build a diagnostic export failure message from task and item fields."""
    message = (
        payload.get(ExportField.ERROR_MESSAGE)
        or payload.get(ExportField.MESSAGE)
        or "Export failed"
    )
    parts = [f"Export {export_dir_id} failed: {message}"]
    error_code = payload.get(ExportField.ERROR_CODE)
    if error_code is not None:
        parts.append(f"error_code={error_code}")
    internal_error_code = payload.get(ExportField.INTERNAL_ERROR_CODE)
    if internal_error_code is not None:
        parts.append(f"internal_error_code={internal_error_code}")

    failed_items = payload.get(ExportField.FAILED_ITEMS) or []
    if failed_items:
        item_parts = []
        for item in failed_items[:5]:
            item_message = (
                item.get(ExportField.ERROR_MESSAGE)
                or item.get(ExportField.MESSAGE)
                or item.get(ExportField.REASON)
                or "unknown"
            )
            item_parts.append(
                "image_id={image_id} error_code={error_code} reason={reason} message={message}".format(
                    image_id=item.get(ExportField.IMAGE_ID),
                    error_code=item.get(ExportField.ERROR_CODE),
                    reason=item.get(ExportField.REASON),
                    message=item_message,
                )
            )
        parts.append(f"failed_items={len(failed_items)}")
        parts.append("item_errors=[" + "; ".join(item_parts) + "]")
    return " | ".join(parts)


class ExportAPI:
    """Start preset-based image exports and subscribe to lifecycle events."""

    def __init__(self, client):
        self._client = client

    # ------------------------------------------------------------------
    # RPC wrappers
    # ------------------------------------------------------------------

    def list_export_presets(self) -> list[dict]:
        """List available export setting presets (saved export configurations).

        Returns a list of preset dicts, each containing ``uuid``, ``name``,
        ``create_time``, and ``update_time``.

        Returns:
            List of export preset info dicts.
        """
        result = self._client.call(ExportCmd.LIST_EXPORT_PRESETS, {})
        return result.get(ExportField.EXPORT_PRESETS, [])

    def start_with_export_preset(
        self,
        project_id: int,
        export_preset_ids: list[str],
        *,
        imageIds: list[int],
        preset_suit_ids: list[str] | None = None,
        export_listener_uuid: str | None = None,
        crop_transparent: bool = False,
    ) -> dict:
        """Export images using saved export setting preset(s).

        Each export preset defines a complete export configuration including
        the export path, format, quality, scale, sharpen, watermark, naming,
        etc.  This is an alternative to :meth:`start_with_custom` where you
        manually specify export options and path.

        Before accepting the export task, the host resolves the effective
        preset suit IDs from the saved configurations and makes every regular
        effect preset available locally. When ``preset_suit_ids`` is provided,
        those override IDs are prepared instead. Sentinel selections that do
        not represent a downloadable effect are left unchanged. The call can
        therefore take longer when preset assets must be downloaded, but the
        accepted export task and its lifecycle events remain asynchronous.

        Args:
            project_id: Target project ID.
            export_preset_ids: One or more export setting preset UUIDs
                (obtained from :meth:`list_export_presets`).
            imageIds: Image IDs to export.
            preset_suit_ids: Optional effect preset IDs to override the
                export preset's built-in effect preset configuration.
            export_listener_uuid: Optional UUID tag for event filtering.
            crop_transparent: When ``True``, crop transparent output to the
                bounding box of visible pixels, removing fully transparent
                margins. Defaults to ``False``. Every selected export preset
                must use an output format with an alpha channel (PNG, TIFF or
                original); a preset that exports JPEG makes the host reject
                the request with code ``400``. See
                :meth:`evoto.export_options.ExportOptions.crop_transparent`
                for the full behaviour. Requires Evoto 8.1.0 or later.

        Returns:
            Host acceptance response including ``accepted``, ``export_dir_id``
            and ``requested_count``. Use :meth:`query` or export lifecycle
            events for ``export_name`` and per-item details. The response is
            returned only after required effect presets are ready; the export
            then continues asynchronously with the existing event contract.
            If preparation fails, the call raises ``ApiError`` instead of
            returning an acceptance response: code ``404`` identifies an
            unknown suit ID, and code ``503`` identifies a download or local
            validation failure.

        Raises:
            ApiError: ``400`` if ``crop_transparent`` is set and a selected
                export preset exports JPEG; ``404`` if an effective preset
                suit ID is unknown; ``503`` if required preset assets cannot
                be downloaded or validated. No export task is accepted in
                any of these cases.
        """
        if not export_preset_ids:
            raise ValueError("export_preset_ids must be a non-empty list")
        payload: dict = {
            ExportField.PROJECT_ID: project_id,
            ExportField.EXPORT_PRESET_IDS: export_preset_ids,
            ExportField.IMAGE_IDS: imageIds,
        }
        if preset_suit_ids is not None:
            payload[ExportField.PRESET_SUIT_IDS] = preset_suit_ids
        if export_listener_uuid:
            payload[ExportField.EXPORT_LISTENER_UUID] = export_listener_uuid
        if crop_transparent:
            payload[ExportField.CROP_TRANSPARENT] = True
        return self._client.call(
            ExportCmd.START_WITH_EXPORT_PRESET,
            payload,
            timeout=_PRESET_PREPARATION_TIMEOUT,
        )

    def subscribe(self, export_listener_uuid: str | None = None) -> dict:
        """Subscribe to export lifecycle events on the host.

        Call this after connecting to start receiving ``export.*`` events.
        If *export_listener_uuid* is provided, only events for exports
        initiated with that UUID will be delivered. Omit it to receive all.

        Args:
            export_listener_uuid: Optional UUID filter. Only exports started
                with the same UUID will trigger events for this subscriber.

        Returns:
            ``{subscribed: true}``
        """
        payload: dict = {}
        if export_listener_uuid:
            payload[ExportField.EXPORT_LISTENER_UUID] = export_listener_uuid
        return self._client.call(ExportCmd.SUBSCRIBE, payload)

    def unsubscribe(self) -> dict:
        """Unsubscribe from export lifecycle events.

        Returns:
            ``{unsubscribed: true}``
        """
        return self._client.call(ExportCmd.UNSUBSCRIBE, {})

    def start_with_custom(
        self,
        project_id: int,
        export_dir: str,
        preset_suit_ids: list[str],
        *,
        imageIds: list[int],
        export_listener_uuid: str | None = None,
        options: dict | None = None,
    ) -> dict:
        """Export images using one or more preset suits.

        This does **not** require the project to be currently open.
        Call :meth:`subscribe` first to receive export lifecycle events.
        Before accepting the export task, the host makes every regular effect
        preset in ``preset_suit_ids`` available locally. Sentinel selections
        that do not represent a downloadable effect are left unchanged. The
        call can therefore take longer when preset assets must be downloaded,
        but the accepted export task and its lifecycle events remain
        asynchronous.

        Args:
            project_id: Target project ID.
            export_dir: Destination directory path.
            preset_suit_ids: One or more preset suit IDs to apply.
            imageIds: Image IDs to export.
            export_listener_uuid: Optional UUID tag for event filtering and
                reconnect recovery.
            options: Optional overrides built with
                :class:`~evoto.export_options.ExportOptions`. Use
                :meth:`~evoto.export_options.ExportOptions.crop_transparent`
                to trim fully transparent margins from PNG/TIFF output.

        Returns:
            Host acceptance response including ``accepted``, ``export_dir_id``,
            ``export_dir`` and ``requested_count``. Use :meth:`query` or export
            lifecycle events for ``export_name`` and per-item details. The
            response is returned only after required effect presets are ready;
            the export then continues asynchronously with the existing event
            contract. If preparation fails, the call raises ``ApiError``
            instead of returning an acceptance response: code ``404``
            identifies an unknown suit ID, and code ``503`` identifies a
            download or local validation failure.

        Raises:
            ApiError: ``400`` if ``options`` enables ``crop_transparent``
                while the effective output format is JPEG; ``404`` if a
                preset suit ID is unknown; ``503`` if required preset assets
                cannot be downloaded or validated. No export task is accepted
                in any of these cases.
        """
        if not preset_suit_ids:
            raise ValueError("preset_suit_ids must be a non-empty list")
        payload: dict = {
            ExportField.PROJECT_ID: project_id,
            ExportField.EXPORT_DIR: export_dir,
            ExportField.PRESET_SUIT_IDS: preset_suit_ids,
            ExportField.IMAGE_IDS: imageIds,
        }
        if export_listener_uuid:
            payload[ExportField.EXPORT_LISTENER_UUID] = export_listener_uuid
        if options:
            payload[ExportField.OPTIONS] = options
        return self._client.call(
            ExportCmd.START_WITH_CUSTOM,
            payload,
            timeout=_PRESET_PREPARATION_TIMEOUT,
        )

    def query(
        self,
        *,
        export_listener_uuid: str | None = None,
        export_dir_id: int | None = None,
        include_items: bool = False,
    ) -> dict:
        """Query export task state from the host.

        If neither parameter is provided, returns all tasks for the current user.

        Args:
            export_listener_uuid: Find all tasks with this listener UUID.
            export_dir_id: Find a specific task by its export_dir_id.
            include_items: Include per-image export result details in each task.

        Returns:
            ``{success, items: [{export_dir_id, export_name, state, progress, items?, ...}]}``.
            ``state`` is the task state, such as ``running``, ``paused``,
            ``completed``, or ``failed``. Failed tasks include ``message``,
            ``error_message``, ``error_code``, and ``failed_items`` when the
            host has item-level failure details.
        """
        payload: dict = {}
        if export_dir_id is not None:
            payload[ExportField.EXPORT_DIR_ID] = export_dir_id
        elif export_listener_uuid:
            payload[ExportField.EXPORT_LISTENER_UUID] = export_listener_uuid
        if include_items:
            payload[ExportField.INCLUDE_ITEMS] = True
        return self._client.call(ExportCmd.QUERY, payload)

    def pause(self, export_dir_id: int) -> dict:
        """Pause an in-progress export task.

        Args:
            export_dir_id: Export task ID returned by
                :meth:`start_with_custom`, :meth:`start_with_export_preset`,
                or :meth:`query`.

        Returns:
            ``{"success": True, "export_dir_id": export_dir_id}``.
        """
        return self._client.call(ExportCmd.PAUSE, {
            ExportField.EXPORT_DIR_ID: export_dir_id,
        })

    def resume(self, export_dir_id: int) -> dict:
        """Resume a paused export task.

        Args:
            export_dir_id: Export task ID to resume.

        Returns:
            ``{"success": True, "export_dir_id": export_dir_id}``.
        """
        return self._client.call(ExportCmd.RESUME, {
            ExportField.EXPORT_DIR_ID: export_dir_id,
        })

    def retry(self, export_dir_id: int) -> dict:
        """Retry failed items in an export task.

        Args:
            export_dir_id: Export task ID whose failed items should be retried.

        Returns:
            ``{"success": True, "export_dir_id": export_dir_id}``.
        """
        return self._client.call(ExportCmd.RETRY, {
            ExportField.EXPORT_DIR_ID: export_dir_id,
        })

    def delete(self, export_dir_id: int) -> dict:
        """Delete an export task.

        Args:
            export_dir_id: Export task ID to delete from the task list.

        Returns:
            ``{"success": True, "export_dir_id": export_dir_id}``.
        """
        return self._client.call(ExportCmd.DELETE, {
            ExportField.EXPORT_DIR_ID: export_dir_id,
        })

    # ------------------------------------------------------------------
    # Event subscription helpers
    # ------------------------------------------------------------------

    def on_started(self, callback: Callable[[dict], None]) -> None:
        """Subscribe to ``export.started`` events.

        Args:
            callback: Function called with the started export payload.
        """
        self._client.on(ExportCmd.STARTED, callback)

    def on_progress(self, callback: Callable[[dict], None]) -> None:
        """Subscribe to ``export.progress`` events.

        Callback receives ``{state, progress, completed_count, ...}``.

        Args:
            callback: Function called whenever export progress changes.
        """
        self._client.on(ExportCmd.PROGRESS, callback)

    def on_item_finished(self, callback: Callable[[dict], None]) -> None:
        """Subscribe to ``export.item_finished`` events.

        Args:
            callback: Function called when one export item finishes.
        """
        self._client.on(ExportCmd.ITEM_FINISHED, callback)

    def on_completed(self, callback: Callable[[dict], None]) -> None:
        """Subscribe to ``export.completed`` events.

        Args:
            callback: Function called with the completed export payload.
        """
        self._client.on(ExportCmd.COMPLETED, callback)

    def on_failed(self, callback: Callable[[dict], None]) -> None:
        """Subscribe to ``export.failed`` events.

        Args:
            callback: Function called with the failed export payload.
        """
        self._client.on(ExportCmd.FAILED, callback)

    def off_started(self, callback: Callable | None = None) -> None:
        """Unregister an ``export.started`` event callback (or all of them
        when ``callback`` is omitted).

        Args:
            callback: Callback to remove. Omit to remove all started-event
                callbacks registered by this client.
        """
        self._client.off(ExportCmd.STARTED, callback)

    def off_progress(self, callback: Callable | None = None) -> None:
        """Unregister an ``export.progress`` event callback (or all of them
        when ``callback`` is omitted).

        Args:
            callback: Callback to remove. Omit to remove all progress-event
                callbacks registered by this client.
        """
        self._client.off(ExportCmd.PROGRESS, callback)

    def off_item_finished(self, callback: Callable | None = None) -> None:
        """Unregister an ``export.item_finished`` event callback (or all of
        them when ``callback`` is omitted).

        Args:
            callback: Callback to remove. Omit to remove all item-finished
                callbacks registered by this client.
        """
        self._client.off(ExportCmd.ITEM_FINISHED, callback)

    def off_completed(self, callback: Callable | None = None) -> None:
        """Unregister an ``export.completed`` event callback (or all of them
        when ``callback`` is omitted).

        Args:
            callback: Callback to remove. Omit to remove all completed-event
                callbacks registered by this client.
        """
        self._client.off(ExportCmd.COMPLETED, callback)

    def off_failed(self, callback: Callable | None = None) -> None:
        """Unregister an ``export.failed`` event callback (or all of them
        when ``callback`` is omitted).

        Args:
            callback: Callback to remove. Omit to remove all failed-event
                callbacks registered by this client.
        """
        self._client.off(ExportCmd.FAILED, callback)

    # ------------------------------------------------------------------
    # High-level blocking wait
    # ------------------------------------------------------------------

    def wait_for_completion(
        self,
        export_dir_id: int,
        *,
        on_progress: Callable[[float], None] | None = None,
        on_item: Callable[[dict], None] | None = None,
        timeout: float = 600,
    ) -> dict:
        """Block until the export identified by *export_dir_id* finishes.

        Internally subscribes to ``export.progress``, ``export.completed``,
        and ``export.failed`` events and waits via :class:`threading.Event`.

        Args:
            export_dir_id: The ``export_dir_id`` returned by :meth:`start_with_custom`
                or :meth:`start_with_export_preset`.
            on_progress: Optional callback receiving progress percentage (0-100).
            on_item: Optional callback receiving each ``export.item_finished`` payload.
            timeout: Maximum seconds to wait.

        Returns:
            The final event payload (completed or failed).

        Raises:
            RuntimeError: If the export fails.
            TimeoutError: If *timeout* is exceeded.
        """
        done = threading.Event()
        result_box: list[dict] = []
        error_box: list[dict] = []

        def _matches(data: dict) -> bool:
            return data.get(ExportField.EXPORT_DIR_ID) == export_dir_id

        def _on_progress(data: dict):
            if _matches(data) and on_progress:
                on_progress(data.get(ExportField.PROGRESS, 0))

        def _on_item(data: dict):
            if _matches(data) and on_item:
                on_item(data)

        def _on_completed(data: dict):
            if _matches(data):
                result_box.append(data)
                done.set()

        def _on_failed(data: dict):
            if _matches(data):
                error_box.append(data)
                done.set()

        self._client.on(ExportCmd.PROGRESS, _on_progress)
        self._client.on(ExportCmd.ITEM_FINISHED, _on_item)
        self._client.on(ExportCmd.COMPLETED, _on_completed)
        self._client.on(ExportCmd.FAILED, _on_failed)

        try:
            if not done.wait(timeout):
                raise TimeoutError(
                    f"Export {export_dir_id} timed out after {timeout}s"
                )
        finally:
            self._client.off(ExportCmd.PROGRESS, _on_progress)
            self._client.off(ExportCmd.ITEM_FINISHED, _on_item)
            self._client.off(ExportCmd.COMPLETED, _on_completed)
            self._client.off(ExportCmd.FAILED, _on_failed)

        if error_box:
            payload = error_box[0]
            raise RuntimeError(_format_export_failure(export_dir_id, payload))

        return result_box[0]
