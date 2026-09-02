"""Library host helpers."""

from __future__ import annotations

from typing import Any, Callable, Literal, TypedDict

from .core.api_commands import LibraryCmd
from .core.api_error_code import ApiErrorCode
from .core.api_fields import LibraryField, MetadataColorLabel, MetadataFlag
from .core._internal.exceptions import ApiError


LibrarySortKey = Literal["capture_time", "filename", "rating", "color_label"]
# Legacy string aliases for the flag filter. The host still accepts these for
# backward compatibility, but new code should use ``MetadataFlag`` members.
LibraryFlagFilter = Literal["flagged", "rejected", "unflagged"]
LibraryEditStatusFilter = Literal["unedited", "edited"]
LibraryExportStatusFilter = Literal["unexported", "exported", "failed"]
LibraryOrientationFilter = Literal["landscape", "portrait", "square"]
LibrarySpaceType = Literal["all", "personal", "team"]
LibraryFormatFilter = Literal[
    "RAW", "JPG", "JPEG", "PNG", "TIFF", "TIF", "HEIC", "BMP", "TSQ"
]


class LibraryImageFilters(TypedDict, total=False):
    """Filter keys accepted by :meth:`LibraryAPI.list_images`.

    Use ``LibraryField`` constants when building dictionaries. The string keys
    are shown here so IDEs can display exactly what the host accepts.
    """

    rating: list[int]
    color_label: list[MetadataColorLabel]
    flag: list[MetadataFlag]
    edit_status: list[LibraryEditStatusFilter]
    export_status: list[LibraryExportStatusFilter]
    format: list[LibraryFormatFilter]
    orientation: list[LibraryOrientationFilter]
    file_name: list[str]
    camera: list[str]
    lens: list[str]


class LibraryAPI:
    """Query library images and update lightweight image labels."""

    def __init__(self, client):
        self._client = client

    def list_images(
        self,
        project_id: int | None = None,
        *,
        filters: LibraryImageFilters | None = None,
        sort: LibrarySortKey | None = None,
        sort_desc: bool = False,
        page: int | None = None,
        page_size: int | None = None,
    ) -> list[dict[str, Any]]:
        """List library images without changing host UI filters.

        Args:
            project_id: Project ID to query. Omit it only when deliberately
                testing host-side missing-parameter handling.
            filters: Optional data filters. Supported keys:
                ``LibraryField.RATING`` (list of 0-5 star values),
                ``LibraryField.COLOR_LABEL`` (list of ``MetadataColorLabel`` members),
                ``LibraryField.FLAG`` (list of ``MetadataFlag`` members; the
                legacy strings ``"flagged"``, ``"rejected"``, ``"unflagged"``
                are still accepted),
                ``LibraryField.EDIT_STATUS`` (``"edited"``, ``"unedited"``),
                ``LibraryField.EXPORT_STATUS`` (``"exported"``, ``"unexported"``, ``"failed"``),
                ``LibraryField.FORMAT`` (``"RAW"``, ``"JPG"``, ``"PNG"``, ``"TIFF"``, etc.),
                ``LibraryField.ORIENTATION`` (``"landscape"``, ``"portrait"``, ``"square"``),
                and ``LibraryField.FILE_NAME`` (list of filename keywords).
                Example: ``{LibraryField.RATING: [2, 3], LibraryField.FLAG: [MetadataFlag.PICK]}``.
            sort: Optional sort keys. Supported values:
                ``LibraryField.CAPTURE_TIME``, ``LibraryField.FILENAME``,
                ``LibraryField.RATING`` and ``LibraryField.COLOR_LABEL``.
                Their string values are ``"capture_time"``, ``"filename"``,
                ``"rating"`` and ``"color_label"``.
                Example: ``LibraryField.CAPTURE_TIME``.
            sort_desc: Sort descending when ``sort`` is provided. Defaults to
                ascending order.
            page: Optional one-based page number.
            page_size: Optional number of images per page.

        Returns:
            List of image payload dicts.
        """
        payload = self._project_payload(project_id=project_id)
        if filters is not None:
            payload[LibraryField.FILTERS] = filters
        if sort is not None:
            payload[LibraryField.SORT] = {"field": sort, "desc": sort_desc}
        if page is not None:
            payload[LibraryField.PAGE] = page
        if page_size is not None:
            payload[LibraryField.PAGE_SIZE] = page_size
        result = self._client.call(LibraryCmd.LIST_IMAGES, payload)
        return result.get(LibraryField.IMAGES, [])

    def update_labels(
        self,
        image_ids: list[int],
        *,
        rating: int | None = None,
        color_label: MetadataColorLabel | None = None,
        flag: MetadataFlag | None = None,
    ) -> dict:
        """Update rating, color label or flag for images.

        Args:
            image_ids: Image IDs to update.
            rating: Optional star rating, ``0`` to ``5``.
            color_label: Optional color label. Use a
                :class:`~evoto.core.api_fields.MetadataColorLabel` member;
                only its values are accepted.
            flag: Optional flag. Use a
                :class:`~evoto.core.api_fields.MetadataFlag` member;
                only its values are accepted.

        Returns:
            Host batch result payload with per-image item statuses.

        Raises:
            ApiError: ``BAD_REQUEST`` when ``rating``, ``color_label`` or
                ``flag`` is outside its valid range.
        """
        if rating is not None and not 0 <= rating <= 5:
            raise ApiError(
                ApiErrorCode.BAD_REQUEST,
                f"rating must be an integer between 0 and 5, got {rating}",
            )
        if color_label is not None:
            try:
                color_label = MetadataColorLabel(color_label)
            except ValueError:
                raise ApiError(
                    ApiErrorCode.BAD_REQUEST,
                    "color_label must be one of "
                    f"{[m.value for m in MetadataColorLabel]}, got {color_label}",
                ) from None
        if flag is not None:
            try:
                flag = MetadataFlag(flag)
            except ValueError:
                raise ApiError(
                    ApiErrorCode.BAD_REQUEST,
                    f"flag must be one of {[m.value for m in MetadataFlag]}, "
                    f"got {flag}",
                ) from None

        payload = {LibraryField.IMAGE_IDS: image_ids}
        if rating is not None:
            payload[LibraryField.RATING] = rating
        if color_label is not None:
            payload[LibraryField.COLOR_LABEL] = color_label
        if flag is not None:
            payload[LibraryField.FLAG] = flag
        return self._client.call(LibraryCmd.UPDATE_LABELS, payload)

    def get_selection(self) -> dict:
        """Return the current host library selection.

        The host response includes ``project_id``, ``selected_count``,
        ``primary_image_id`` when present, and ``images`` items containing
        ``id``, ``origin_path`` and ``primary``.
        """
        return self._client.call(LibraryCmd.GET_SELECTION, {})

    def set_selection(
        self,
        image_ids: list[int],
        *,
        primary_image_id: int | None = None,
    ) -> dict:
        """Replace the current host library selection.

        The host clears the previous primary flag and marks
        ``primary_image_id`` as the new primary image. If omitted, the host uses
        the first image ID as primary.
        """
        payload = {LibraryField.IMAGE_IDS: image_ids}
        if primary_image_id is not None:
            payload[LibraryField.PRIMARY_IMAGE_ID] = primary_image_id
        return self._client.call(LibraryCmd.SET_SELECTION, payload)

    def add_selection(self, image_ids: list[int]) -> dict:
        """Add image IDs as normal selected images.

        This does not change the current primary image.
        """
        payload = {LibraryField.IMAGE_IDS: image_ids}
        return self._client.call(LibraryCmd.ADD_SELECTION, payload)

    def clear_selection(self, image_ids: list[int] | None = None) -> dict:
        """Clear non-primary images from the current host library selection.

        Args:
            image_ids: Optional image IDs to clear. Omit to clear every
                non-primary selected image. The primary image cannot be cleared
                by this method.
        """
        payload = {}
        if image_ids is not None:
            payload[LibraryField.IMAGE_IDS] = image_ids
        return self._client.call(LibraryCmd.CLEAR_SELECTION, payload)

    def list_spaces(self, space_type: LibrarySpaceType = "all") -> list[dict[str, Any]]:
        """List personal and team spaces.

        Args:
            space_type: ``"all"``, ``"personal"``, or ``"team"``.

        Returns:
            List of space payloads. Each item includes ``space_id``, ``name``
            and ``type``.
        """
        result = self._client.call(LibraryCmd.LIST_SPACES, {LibraryField.TYPE: space_type})
        return result.get(LibraryField.SPACES, [])

    def current_space(self) -> dict[str, Any]:
        """Return the currently active host space."""
        return self._client.call(LibraryCmd.CURRENT_SPACE, {}).get(LibraryField.SPACE, {})

    def switch_space(self, space_id: int) -> dict:
        """Switch the active host space.

        The call returns ``status="pending"`` after the host accepts the
        request. Listen to ``library.switchSpace.completed`` or
        ``library.switchSpace.failed`` for the final result.

        Args:
            space_id: Target personal or team space ID.

        Returns:
            Host response with ``success``, ``status`` and the target ``space``
            payload.
        """
        return self._client.call(LibraryCmd.SWITCH_SPACE, {LibraryField.SPACE_ID: space_id})

    def on_switch_space_completed(self, callback: Callable[[dict], None]) -> None:
        """Fired after ``library.switchSpace`` finishes refreshing the Library UI.

        Payload includes ``space_id`` and the switched ``space`` object.
        """
        self._client.on(LibraryCmd.SWITCH_SPACE_COMPLETED, callback)

    def on_switch_space_failed(self, callback: Callable[[dict], None]) -> None:
        """Fired when ``library.switchSpace`` fails after being accepted.

        Payload includes ``space_id`` and failure ``message``.
        """
        self._client.on(LibraryCmd.SWITCH_SPACE_FAILED, callback)

    def off_switch_space_completed(self, callback: Callable | None = None) -> None:
        """Unregister ``library.switchSpace.completed`` listeners."""
        self._client.off(LibraryCmd.SWITCH_SPACE_COMPLETED, callback)

    def off_switch_space_failed(self, callback: Callable | None = None) -> None:
        """Unregister ``library.switchSpace.failed`` listeners."""
        self._client.off(LibraryCmd.SWITCH_SPACE_FAILED, callback)

    @staticmethod
    def _project_payload(
        *,
        project_id: int | None,
    ) -> dict:
        payload = {}
        if project_id is not None:
            payload[LibraryField.PROJECT_ID] = project_id
        return payload
