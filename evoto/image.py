"""Image import / listing wrappers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .core.api_commands import ImageCmd
from .core.api_fields import DeleteMode, Field, ImageField


@dataclass(frozen=True)
class ImageInfo:
    """Single image details returned by ``image.info``.

    ``metadata`` is an optional, nested ``{category: {field: value}}`` dict
    populated when ``include_metadata=True`` (default). Empty groups are
    omitted, so callers should use ``.get``.

    Attributes:
        id: Image ID.
        filename: File name displayed by the host.
        origin_path: Absolute path to the original image file.
        project_id: ID of the project that owns the image.
        format: Image format label, such as ``JPG``, ``PNG``, ``RAW``,
            ``TIFF``, ``HEIC``, ``BMP`` or ``TSQ``.
        width: Original image width in pixels.
        height: Original image height in pixels.
        file_size: Original file size in bytes.
        metadata: Optional metadata grouped by category. Empty when metadata
            is not requested or unavailable.
    """

    id: int
    filename: str
    origin_path: str
    project_id: int
    format: str
    width: int
    height: int
    file_size: int
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> ImageInfo:
        raw_metadata = d.get(ImageField.METADATA) or {}
        metadata = raw_metadata if isinstance(raw_metadata, dict) else {}
        return cls(
            id=d.get(Field.ID, 0),
            filename=d.get(ImageField.FILENAME, ""),
            origin_path=d.get(ImageField.ORIGIN_PATH, ""),
            project_id=d.get(ImageField.PROJECT_ID, 0),
            format=d.get(ImageField.FORMAT, ""),
            width=d.get(ImageField.WIDTH, 0),
            height=d.get(ImageField.HEIGHT, 0),
            file_size=d.get(ImageField.FILE_SIZE, 0),
            metadata=metadata,
        )


class ImageAPI:
    """Import and query helpers for project images."""

    def __init__(self, client):
        self._client = client

    def import_files(
        self,
        paths: list,
        *,
        project_id: int | None = None,
        project_name: str | None = None,
        project_group_id: int | None = None,
        use_current_project: bool = False,
        allow_cross_cloud_sync: bool = False,
        data_mode: bool = False,
        import_listener_uuid: str | None = None,
        timeout_ms: int = 300000,
    ) -> dict:
        """Import files or folders into a project synchronously.

        ``image.import`` blocks until the import finishes and returns the host
        result payload directly.

        Args:
            paths: File or directory paths to import. Must contain at least
                one path.
            project_id: Target project ID. Ignored when
                ``use_current_project`` is true or ``project_name`` is used.
            project_name: Create or find a project by name when
                ``project_id`` is not supplied.
            project_group_id: Parent group ID used when creating a project
                from ``project_name``.
            use_current_project: Prefer the currently selected project in
                the host. Falls back to explicit project arguments when no
                current project is available.
            allow_cross_cloud_sync: When creating a project by name, enable
                cross-cloud sync for the new project.
            data_mode: Use a background-safe path that does not depend on the
                currently open UI state.
            import_listener_uuid: Optional UUID used to correlate import
                responses and lifecycle events.
            timeout_ms: Maximum wait time in milliseconds. Defaults to
                ``300000``.

        Returns:
            Host result payload containing ``success``, ``project_id``,
            ``added_count``, ``repeat_count`` and ``images``.
        """
        return self._client.call(
            ImageCmd.IMPORT,
            self._build_import_payload(
                paths=paths,
                project_id=project_id,
                project_name=project_name,
                project_group_id=project_group_id,
                use_current_project=use_current_project,
                allow_cross_cloud_sync=allow_cross_cloud_sync,
                data_mode=data_mode,
                import_listener_uuid=import_listener_uuid,
                timeout_ms=timeout_ms,
            ),
        )

    def import_files_async(
        self,
        paths: list,
        *,
        project_id: int | None = None,
        project_name: str | None = None,
        project_group_id: int | None = None,
        use_current_project: bool = False,
        allow_cross_cloud_sync: bool = False,
        data_mode: bool = False,
        import_listener_uuid: str | None = None,
    ) -> dict:
        """Start an asynchronous image import.

        Returns the immediate acceptance payload, including ``import_id`` when
        provided by the host.

        Args:
            paths: File or directory paths to import. Must contain at least
                one path.
            project_id: Target project ID. Ignored when
                ``use_current_project`` is true or ``project_name`` is used.
            project_name: Create or find a project by name when
                ``project_id`` is not supplied.
            project_group_id: Parent group ID used when creating a project
                from ``project_name``.
            use_current_project: Prefer the currently selected project in
                the host.
            allow_cross_cloud_sync: When creating a project by name, enable
                cross-cloud sync for the new project.
            data_mode: Use a background-safe path that does not depend on the
                currently open UI state.
            import_listener_uuid: Optional UUID used to correlate import
                responses and lifecycle events.

        Returns:
            Immediate acceptance payload with ``status``, ``import_id`` and
            ``project_id``. Completion is delivered through import events.
        """
        return self._client.call(
            ImageCmd.IMPORT_ASYNC,
            self._build_import_payload(
                paths=paths,
                project_id=project_id,
                project_name=project_name,
                project_group_id=project_group_id,
                use_current_project=use_current_project,
                allow_cross_cloud_sync=allow_cross_cloud_sync,
                data_mode=data_mode,
                import_listener_uuid=import_listener_uuid,
            ),
        )

    def subscribe(self, import_listener_uuid: str | None = None) -> dict:
        """Subscribe to import lifecycle events on the host.

        Args:
            import_listener_uuid: Optional UUID filter. When provided, only
                imports started with the same UUID emit events to this
                subscriber.

        Returns:
            ``{"subscribed": True}`` on success.
        """
        payload = {}
        if import_listener_uuid:
            payload[ImageField.IMPORT_LISTENER_UUID] = import_listener_uuid
        return self._client.call(ImageCmd.SUBSCRIBE, payload)

    def unsubscribe(self) -> dict:
        """Unsubscribe from import lifecycle events.

        Returns:
            ``{"unsubscribed": True}`` on success.
        """
        return self._client.call(ImageCmd.UNSUBSCRIBE, {})

    def on_completed(self, callback: Callable[[dict], None]) -> None:
        """Subscribe to ``import.completed`` events.

        Args:
            callback: Function called with the completed import payload.
        """
        self._client.on(ImageCmd.COMPLETED, callback)

    def on_started(self, callback: Callable[[dict], None]) -> None:
        """Subscribe to ``import.started`` events.

        Args:
            callback: Function called with the import-start payload.
        """
        self._client.on(ImageCmd.STARTED, callback)

    def on_progress(self, callback: Callable[[dict], None]) -> None:
        """Subscribe to ``import.progress`` events.

        Args:
            callback: Function called with progress payloads containing
                completed and total counts when available.
        """
        self._client.on(ImageCmd.PROGRESS, callback)

    def on_failed(self, callback: Callable[[dict], None]) -> None:
        """Subscribe to ``import.failed`` events.

        Args:
            callback: Function called with the failed import payload.
        """
        self._client.on(ImageCmd.FAILED, callback)

    def off_completed(self, callback: Callable | None = None) -> None:
        """Unregister ``import.completed`` event callbacks.

        Args:
            callback: Callback to remove. Omit to remove all completed-event
                callbacks registered by this client.
        """
        self._client.off(ImageCmd.COMPLETED, callback)

    def off_started(self, callback: Callable | None = None) -> None:
        """Unregister ``import.started`` event callbacks.

        Args:
            callback: Callback to remove. Omit to remove all started-event
                callbacks registered by this client.
        """
        self._client.off(ImageCmd.STARTED, callback)

    def off_progress(self, callback: Callable | None = None) -> None:
        """Unregister ``import.progress`` event callbacks.

        Args:
            callback: Callback to remove. Omit to remove all progress-event
                callbacks registered by this client.
        """
        self._client.off(ImageCmd.PROGRESS, callback)

    def off_failed(self, callback: Callable | None = None) -> None:
        """Unregister ``import.failed`` event callbacks.

        Args:
            callback: Callback to remove. Omit to remove all failed-event
                callbacks registered by this client.
        """
        self._client.off(ImageCmd.FAILED, callback)

    def list(
        self,
        project_id: int | None = None,
        *,
        data_mode: bool = False,
        use_current_project: bool = False,
    ) -> list:
        """List images inside a project.

        Args:
            project_id: Project ID to list. Ignored when
                ``use_current_project`` is true.
            data_mode: Use a background-safe path that does not depend on the
                currently open UI state.
            use_current_project: Prefer the currently selected project in
                the host.

        Returns:
            List of image dicts containing at least ``id``, ``filename`` and
            ``origin_path``.
        """
        payload = {}
        if use_current_project:
            payload[ImageField.USE_CURRENT_PROJECT] = True
        elif project_id is not None:
            payload[ImageField.PROJECT_ID] = project_id
        if data_mode:
            payload[ImageField.DATA_MODE] = True
        result = self._client.call(ImageCmd.LIST, payload)
        return result.get(ImageField.IMAGES, [])

    def info(self, image_id: int, *, include_metadata: bool = True) -> ImageInfo:
        """Return basic information for a single image by its ID.

        When ``include_metadata`` is True (default), EXIF/IPTC metadata grouped
        by metadata category is attached to :attr:`ImageInfo.metadata`. Pass
        ``False`` to skip the metadata query on the host side for lightweight
        lookups.

        Args:
            image_id: Image ID to query.
            include_metadata: Include metadata groups when true.

        Returns:
            :class:`ImageInfo` for the requested image.
        """
        payload = {ImageField.IMAGE_ID: image_id}
        if not include_metadata:
            payload[ImageField.INCLUDE_METADATA] = False
        result = self._client.call(ImageCmd.INFO, payload)
        return ImageInfo.from_dict(result)

    def delete(self, imageIds: list[int], *, delete_mode: str = DeleteMode.RECYCLE) -> dict:
        """Start deleting images by ID.

        The host runs one image delete task at a time. While a delete task is
        still running, another ``image.delete`` request raises ``ApiError`` with
        a conflict error from the host.

        Args:
            imageIds: Image IDs to delete.
            delete_mode: Delete behavior. Use ``DeleteMode.RECYCLE`` to move
                images to recycle bin, ``DeleteMode.REMOVE`` to remove them
                from the project, or ``DeleteMode.TRASH`` to move them to the
                system trash.

        Returns:
            Dict containing ``success``, ``accepted``, ``status`` and
            ``requested_count``.
        """
        return self._client.call(
            ImageCmd.DELETE,
            {
                ImageField.IMAGE_IDS: imageIds,
                ImageField.DELETE_MODE: delete_mode,
            },
        )

    @staticmethod
    def _build_import_payload(
        *,
        paths: list,
        project_id: int | None,
        project_name: str | None,
        project_group_id: int | None,
        use_current_project: bool,
        allow_cross_cloud_sync: bool,
        data_mode: bool,
        import_listener_uuid: str | None,
        timeout_ms: int | None = None,
    ) -> dict:
        payload = {ImageField.PATHS: paths}

        if use_current_project:
            payload[ImageField.USE_CURRENT_PROJECT] = True
        elif project_id is not None:
            payload[ImageField.PROJECT_ID] = project_id
        elif project_name:
            payload[ImageField.PROJECT_NAME] = project_name

        if project_group_id is not None:
            payload[ImageField.PROJECT_GROUP_ID] = project_group_id
        if allow_cross_cloud_sync:
            payload[ImageField.ALLOW_CROSS_CLOUD_SYNC] = True
        if data_mode:
            payload[ImageField.DATA_MODE] = True
        if import_listener_uuid:
            payload[ImageField.IMPORT_LISTENER_UUID] = import_listener_uuid
        if timeout_ms is not None:
            payload[ImageField.TIMEOUT_MS] = timeout_ms

        return payload
