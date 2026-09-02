"""Culling host helpers."""

from __future__ import annotations

from typing import TypedDict

from .core.api_commands import CullingCmd
from .core.api_fields import CullingField, ProjectField


_REMOVED_IMAGE_RESULT_FIELDS = ("duplicate",)


class CullingResultFilters(TypedDict, total=False):
    """Filter keys accepted by :meth:`CullingAPI.list_results`.

    Use :class:`evoto.core.api_fields.CullingField` constants when building
    dictionaries. The string keys are listed here so IDEs can show exactly what
    the host accepts.
    """

    ai_selected: bool
    candidate: bool
    blurry: bool
    sharp: bool
    closed_eyes: bool
    overexposed: bool
    underexposed: bool
    similar: bool
    group_id: int
    cluster_id: int


class CullingAPI:
    """Read culling status and result data from the host."""

    def __init__(self, client):
        self._client = client

    def status(
        self,
        project_id: int | None = None,
        *,
        use_current_project: bool = False,
        image_ids: list[int] | None = None,
    ) -> dict:
        """Return culling status for a project.

        Args:
            project_id: Project ID to inspect. Ignored when
                ``use_current_project`` is true.
            use_current_project: Prefer the host's current project.
            image_ids: Optional image IDs to limit the status counts. Empty or
                omitted means all images in the current project.

        Returns:
            Host status payload. The ``status`` field uses
            :class:`evoto.core.api_fields.CullingStatusValue` values.
        """
        payload = self._project_payload(
            project_id=project_id,
            use_current_project=use_current_project,
        )
        if image_ids is not None:
            payload[CullingField.IMAGE_IDS] = image_ids
        return self._client.call(CullingCmd.STATUS, payload)

    def start(
        self,
        project_id: int | None = None,
        *,
        use_current_project: bool = False,
        mode: str | None = None,
    ) -> dict:
        """Request culling start.

        The host starts culling only when the target project is currently
        loaded in the UI. Other projects are rejected by the host. A successful
        response means the request was accepted; progress and final state are
        delivered through ``culling.started``, ``culling.progress``,
        ``culling.completed`` and ``culling.failed`` events.

        Args:
            project_id: Project ID to process. Ignored when
                ``use_current_project`` is true.
            use_current_project: Prefer the host's current project.
            mode: Optional host culling mode.

        Returns:
            Host acceptance payload.
        """
        payload = self._project_payload(
            project_id=project_id,
            use_current_project=use_current_project,
        )
        if mode is not None:
            payload[CullingField.MODE] = mode
        return self._client.call(CullingCmd.START, payload)

    def restart(
        self,
        project_id: int | None = None,
        *,
        use_current_project: bool = False,
        mode: str | None = None,
    ) -> dict:
        """Request culling restart.

        The host restarts culling only when the target project is currently
        loaded in the UI. Other projects are rejected by the host. A successful
        response means the restart request was accepted; progress and final
        state are delivered through ``culling.started``,
        ``culling.progress``, ``culling.completed`` and ``culling.failed``
        events.

        Args:
            project_id: Project ID to process. Ignored when
                ``use_current_project`` is true.
            use_current_project: Prefer the host's current project.
            mode: Optional host culling mode.

        Returns:
            Host acceptance or skipped payload.
        """
        payload = self._project_payload(
            project_id=project_id,
            use_current_project=use_current_project,
        )
        if mode is not None:
            payload[CullingField.MODE] = mode
        return self._client.call(CullingCmd.RESTART, payload)

    def stop(
        self,
        project_id: int | None = None,
        *,
        use_current_project: bool = False,
    ) -> dict:
        """Request culling stop.

        The host stops culling only when the target project is currently loaded
        in the UI. Other projects are rejected by the host. A successful
        response means the stop request was accepted; final cancellation state
        is delivered through the ``culling.canceled`` event.

        Args:
            project_id: Project ID to stop. Ignored when
                ``use_current_project`` is true.
            use_current_project: Prefer the host's current project.

        Returns:
            Host stop acceptance or skipped payload.
        """
        payload = self._project_payload(
            project_id=project_id,
            use_current_project=use_current_project,
        )
        return self._client.call(CullingCmd.STOP, payload)

    def scan_qr_codes(
        self,
        project_id: int | None = None,
        *,
        use_current_project: bool = False,
        image_ids: list[int] | None = None,
        force: bool = False,
    ) -> dict:
        """Scan project images for QR Codes.

        The host performs the scan asynchronously. Progress and final state are
        delivered through ``culling.qrCode.started``,
        ``culling.qrCode.progress``, ``culling.qrCode.completed`` and
        ``culling.qrCode.failed`` events. When ``force`` is false, the host
        scans only images that have not been checked before.

        Args:
            project_id: Project ID to process. Ignored when
                ``use_current_project`` is true.
            use_current_project: Prefer the host's current project.
            image_ids: Optional image IDs to limit the scan. Empty or omitted
                means all images in the current project.
            force: Re-scan images even when they were checked before.

        Returns:
            Payload with ``task_id``, ``project_id``, ``status``,
            ``success`` and ``results``. The ``results`` array only
            contains images where QR codes were found. Each result row
            has ``image_id``, ``absolute_path``, ``qr_code_checked``,
            ``has_qr_code`` and ``qr_code_content`` (a list of decoded
            QR code strings).
        """
        payload = self._project_payload(
            project_id=project_id,
            use_current_project=use_current_project,
        )
        if image_ids is not None:
            payload[CullingField.IMAGE_IDS] = image_ids
        payload[CullingField.FORCE] = force
        return self._client.call(CullingCmd.QR_CODE_SCAN, payload)

    def list_qr_code_results(
        self,
        project_id: int | None = None,
        *,
        use_current_project: bool = False,
        image_ids: list[int] | None = None,
    ) -> list:
        """List persisted QR Code scan results.

        Args:
            project_id: Project ID to inspect. Ignored when
                ``use_current_project`` is true.
            use_current_project: Prefer the host's current project.
            image_ids: Optional image IDs to limit returned rows. Empty or
                omitted means all images in the current project.

        Returns:
            List of rows where QR codes were found. Each row contains
            ``image_id``, ``absolute_path``, ``qr_code_checked``,
            ``has_qr_code`` and ``qr_code_content`` (a list of decoded
            QR code strings).
        """
        payload = self._project_payload(
            project_id=project_id,
            use_current_project=use_current_project,
        )
        if image_ids is not None:
            payload[CullingField.IMAGE_IDS] = image_ids
        result = self._client.call(CullingCmd.QR_CODE_LIST_RESULTS, payload)
        return result.get(CullingField.RESULTS, [])

    def list_results(
        self,
        project_id: int | None = None,
        *,
        use_current_project: bool = False,
        image_ids: list[int] | None = None,
        filters: CullingResultFilters | None = None,
    ) -> list:
        """List image-level culling results.

        The host rejects this request while culling is running. Use
        :meth:`status` or culling progress events until the task finishes.

        Args:
            project_id: Project ID to inspect. Ignored when
                ``use_current_project`` is true.
            use_current_project: Prefer the host's current project.
            image_ids: Optional image IDs to limit the result set. Empty or
                omitted means all images in the current project.
            filters: Optional image-level culling filters. Supported keys:
                ``CullingField.AI_SELECTED``, ``CullingField.CANDIDATE``,
                ``CullingField.BLURRY``, ``CullingField.SHARP``,
                ``CullingField.CLOSED_EYES``,
                ``CullingField.OVEREXPOSED``, ``CullingField.UNDEREXPOSED``,
                ``CullingField.SIMILAR``, ``CullingField.GROUP_ID`` and
                ``CullingField.CLUSTER_ID``.
                Example: ``{CullingField.AI_SELECTED: True, CullingField.SHARP: True}``.

        Returns:
            List of image-level culling result payload dicts.
        """
        payload = self._project_payload(
            project_id=project_id,
            use_current_project=use_current_project,
        )
        if image_ids is not None:
            payload[CullingField.IMAGE_IDS] = image_ids
        if filters is not None:
            payload[CullingField.FILTERS] = filters
        result = self._client.call(CullingCmd.LIST_RESULTS, payload)
        return [
            self._image_result_payload(item)
            for item in result.get(CullingField.RESULTS, [])
        ]

    def list_faces(
        self,
        project_id: int | None = None,
        *,
        use_current_project: bool = False,
        image_ids: list[int] | None = None,
    ) -> list:
        """List face records attached to project images.

        The host rejects this request while culling is running. Use
        :meth:`status` or culling progress events until the task finishes.

        Args:
            project_id: Project ID to inspect. Ignored when
                ``use_current_project`` is true.
            use_current_project: Prefer the host's current project.
            image_ids: Optional image IDs to limit the result set. Empty or
                omitted means all images in the current project.

        Returns:
            List of face payload dicts from the host face records.
        """
        payload = self._project_payload(
            project_id=project_id,
            use_current_project=use_current_project,
        )
        if image_ids is not None:
            payload[CullingField.IMAGE_IDS] = image_ids
        result = self._client.call(CullingCmd.LIST_FACES, payload)
        return result.get(CullingField.FACES, [])

    def list_clusters(
        self,
        project_id: int | None = None,
        *,
        use_current_project: bool = False,
        image_ids: list[int] | None = None,
        cluster_type: str | None = None,
    ) -> list:
        """List culling clusters for a project.

        The host rejects this request while culling is running. Use
        :meth:`status` or culling progress events until the task finishes.

        Args:
            project_id: Project ID to inspect. Ignored when
                ``use_current_project`` is true.
            use_current_project: Prefer the host's current project.
            image_ids: Optional image IDs to limit returned clusters. Empty or
                omitted means all images in the current project.
            cluster_type: Optional host cluster type.

        Returns:
            List of cluster payload dicts.
        """
        payload = self._project_payload(
            project_id=project_id,
            use_current_project=use_current_project,
        )
        if image_ids is not None:
            payload[CullingField.IMAGE_IDS] = image_ids
        if cluster_type is not None:
            payload[CullingField.CLUSTER_TYPE] = cluster_type
        result = self._client.call(CullingCmd.LIST_CLUSTERS, payload)
        return result.get(CullingField.CLUSTERS, [])

    @staticmethod
    def _project_payload(
        *,
        project_id: int | None,
        use_current_project: bool,
    ) -> dict:
        payload = {}
        if use_current_project:
            payload[ProjectField.USE_CURRENT_PROJECT] = True
        elif project_id is not None:
            payload[CullingField.PROJECT_ID] = project_id
        return payload

    @staticmethod
    def _image_result_payload(item: dict) -> dict:
        return {
            key: value
            for key, value in item.items()
            if key not in _REMOVED_IMAGE_RESULT_FIELDS
        }
