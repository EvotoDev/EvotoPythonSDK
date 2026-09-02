"""Metadata host helpers."""

from __future__ import annotations

from typing import TypedDict

from .core.api_commands import MetadataCmd
from .core.api_error_code import ApiErrorCode
from .core.api_fields import MetadataColorLabel, MetadataField, MetadataFlag
from .core._internal.exceptions import ApiError


class MetadataEditableFields(TypedDict, total=False):
    """Editable fields accepted by :meth:`MetadataAPI.write`.

    Use :class:`evoto.core.api_fields.MetadataField` constants when building
    dictionaries. String keys are listed here so IDEs can show the payload
    shape accepted by the host.

    ``supplemental_categories`` maps to the IPTC "Supplemental Categories"
    field (XMP ``photoshop:SupplementalCategories``), not to keywords
    (``dc:subject``). It accepts a comma-separated string or a list of strings.
    """

    title: str
    caption: str
    creator: str
    copyright: str
    supplemental_categories: str | list[str]
    rating: int
    color_label: MetadataColorLabel
    flag: MetadataFlag


def _validate_label_fields(fields: MetadataEditableFields) -> None:
    """Reject out-of-range rating / color_label / flag before the RPC.

    ``color_label`` and ``flag`` are constrained to
    :class:`~evoto.core.api_fields.MetadataColorLabel` /
    :class:`~evoto.core.api_fields.MetadataFlag` values; ``rating`` to 0-5.

    Raises:
        ApiError: ``BAD_REQUEST`` when a label field is out of range.
    """
    rating = fields.get(MetadataField.RATING)
    if rating is not None and not 0 <= rating <= 5:
        raise ApiError(
            ApiErrorCode.BAD_REQUEST,
            f"rating must be an integer between 0 and 5, got {rating}",
        )
    color_label = fields.get(MetadataField.COLOR_LABEL)
    if color_label is not None:
        try:
            MetadataColorLabel(color_label)
        except ValueError:
            raise ApiError(
                ApiErrorCode.BAD_REQUEST,
                "color_label must be one of "
                f"{[m.value for m in MetadataColorLabel]}, got {color_label}",
            ) from None
    flag = fields.get(MetadataField.FLAG)
    if flag is not None:
        try:
            MetadataFlag(flag)
        except ValueError:
            raise ApiError(
                ApiErrorCode.BAD_REQUEST,
                f"flag must be one of {[m.value for m in MetadataFlag]}, "
                f"got {flag}",
            ) from None


class MetadataAPI:
    """Read and write image metadata through host RPC."""

    def __init__(self, client):
        self._client = client

    def read(self, image_ids: list[int], *, source: str = "evoto") -> list:
        """Read metadata for image IDs.

        Args:
            image_ids: Image IDs to read.
            source: Metadata source. The first host implementation supports
                ``"evoto"`` for data-backed metadata.

        Returns:
            List of image metadata objects. Each item contains ``image_id``,
            ``filename``, ``absolute_path`` and ``metadata``.
        """
        payload = {
            MetadataField.IMAGE_IDS: image_ids,
            MetadataField.SOURCE: source,
        }
        result = self._client.call(MetadataCmd.READ, payload)
        return result.get(MetadataField.METADATA, [])

    def write(self, image_ids: list[int], fields: MetadataEditableFields) -> dict:
        """Write editable metadata fields for image IDs.

        Args:
            image_ids: Image IDs to update.
            fields: Editable metadata fields. Supported keys:
                ``MetadataField.TITLE``, ``MetadataField.CAPTION``,
                ``MetadataField.CREATOR``, ``MetadataField.COPYRIGHT``,
                ``MetadataField.SUPPLEMENTAL_CATEGORIES``,
                ``MetadataField.RATING``,
                ``MetadataField.COLOR_LABEL`` and ``MetadataField.FLAG``.
                ``rating`` is ``0`` to ``5``. Use ``MetadataColorLabel`` and
                ``MetadataFlag`` members for color-label and flag values; only
                their values are accepted. ``supplemental_categories`` maps to
                IPTC Supplemental Categories (XMP
                ``photoshop:SupplementalCategories``), not keywords
                (``dc:subject``), and accepts a CSV string or list of strings.

        Returns:
            Host batch result payload with per-image item statuses.

        Raises:
            ApiError: ``BAD_REQUEST`` when ``rating``, ``color_label`` or
                ``flag`` in ``fields`` is out of range.
        """
        _validate_label_fields(fields)
        payload = {
            MetadataField.IMAGE_IDS: image_ids,
            MetadataField.FIELDS: fields,
        }
        return self._client.call(MetadataCmd.WRITE, payload)

    def read_from_file(self, image_ids: list[int]) -> dict:
        """Read file metadata into the host data store for image IDs.

        The host performs the file read asynchronously and sends count-based
        progress via ``metadata.readFromFile.started``,
        ``metadata.readFromFile.progress``, ``metadata.readFromFile.completed``
        and ``metadata.readFromFile.failed``. Use ``completed_count`` and
        ``requested_count`` for progress such as ``2/10``.

        Args:
            image_ids: Image IDs to refresh.

        Returns:
            Host batch result payload with per-image item statuses.
        """
        payload = {MetadataField.IMAGE_IDS: image_ids}
        return self._client.call(MetadataCmd.READ_FROM_FILE, payload)

    def save_to_file(
        self,
        image_ids: list[int],
        *,
        sidecar: bool = True,
        fields: MetadataEditableFields | None = None,
    ) -> dict:
        """Save host metadata to the image file or sidecar for image IDs.

        The host performs the save work asynchronously and sends count-based progress via
        ``metadata.saveToFile.started``, ``metadata.saveToFile.progress``,
        ``metadata.saveToFile.completed`` and ``metadata.saveToFile.failed``.
        Use ``completed_count`` and ``requested_count`` for progress such as
        ``2/10``.
        The call still returns the final batch result when the host task
        finishes.

        Args:
            image_ids: Image IDs to save.
            sidecar: Save to a sidecar file when supported by the host.
            fields: Optional editable metadata fields to merge with host
                metadata before saving to the file. Same shape as
                :meth:`write`. The host does not write these values back to
                its data store.

        Returns:
            Host batch result payload with per-image item statuses.

        Raises:
            ApiError: ``BAD_REQUEST`` when ``rating``, ``color_label`` or
                ``flag`` in ``fields`` is out of range.
        """
        payload = {
            MetadataField.IMAGE_IDS: image_ids,
            MetadataField.SIDECAR: sidecar,
        }
        if fields is not None:
            _validate_label_fields(fields)
            payload[MetadataField.FIELDS] = fields
        return self._client.call(MetadataCmd.SAVE_TO_FILE, payload)
