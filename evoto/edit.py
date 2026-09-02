"""Edit status and workflow host helpers."""

from __future__ import annotations

from .core.api_commands import EditCmd
from .core.api_fields import EditField, ProjectField


class EditAPI:
    """Read edit summaries and call guarded edit workflows."""

    def __init__(self, client):
        self._client = client

    def status(self, project_id: int, image_ids: list[int] | None = None) -> list[dict]:
        """Return edit status summaries.

        Args:
            project_id: Project ID to inspect.
            image_ids: Optional image IDs to inspect. Omit to inspect all
                non-recycled images in the project.

        Returns:
            List of per-image edit summary payload dicts. Each item may include
            ``has_edit``, ``has_color``, ``has_ai_color``, ``has_portrait``,
            ``has_background``, ``has_crop``, ``has_clothes``, ``has_pet``,
            and ``has_preset``.

        Raises:
            ApiError: The host returns conflict when another edit status query
                is still running.
        """
        payload = {ProjectField.PROJECT_ID: project_id}
        if image_ids is not None:
            payload[EditField.IMAGE_IDS] = image_ids
        result = self._client.call(EditCmd.STATUS, payload)
        return result.get(EditField.STATUS, [])

    def sync_from(
        self,
        source_image_id: int,
        target_image_ids: list[int],
        modules: list[str] | None = None,
    ) -> dict:
        """Sync the current source edit recipe to target images.

        Args:
            source_image_id: Source image ID.
            target_image_ids: Target image IDs.
            modules: Optional module names from
                :class:`evoto.core.api_fields.EditModuleValue`.

        Returns:
            Host workflow response with accepted/skipped/failed counts and
            per-image items. When ``modules`` is provided, those module names
            override the host saved/default sync settings. When omitted, the
            host uses its saved or default sync settings.
        """
        payload = {
            EditField.SOURCE_IMAGE_ID: source_image_id,
            EditField.TARGET_IMAGE_IDS: target_image_ids,
        }
        if modules is not None:
            payload[EditField.MODULES] = modules
        return self._client.call(EditCmd.SYNC_FROM, payload)

    def reset(self, image_ids: list[int], modules: list[str] | None = None) -> dict:
        """Reset edit effects for image IDs.

        Args:
            image_ids: Image IDs to reset.
            modules: Optional module names from
                :class:`evoto.core.api_fields.EditModuleValue`.

        Returns:
            Host workflow response with accepted/skipped/failed counts and
            per-image items. When ``modules`` is provided, the host applies
            default parameters for those modules and leaves other modules
            unchanged. When omitted, the host resets all effects.
        """
        payload = {EditField.IMAGE_IDS: image_ids}
        if modules is not None:
            payload[EditField.MODULES] = modules
        return self._client.call(EditCmd.RESET, payload)

    def create_virtual_copy(self, image_id: int) -> dict:
        """Create a virtual copy for one image in the current project.

        Args:
            image_id: Source image ID.

        Returns:
            Host workflow response with batch counts and per-image items. The
            host queues the existing product virtual-copy workflow and reports
            the source image as accepted when the request is submitted.
        """
        return self._client.call(EditCmd.CREATE_VIRTUAL_COPY, {EditField.IMAGE_ID: image_id})
