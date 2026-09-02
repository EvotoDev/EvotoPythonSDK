from __future__ import annotations

"""Preset host helpers."""

from typing import Any, Callable

from .core.api_commands import PresetCmd
from .core.api_error_code import ApiErrorCode
from .core.api_fields import PresetField, Field
from .core._internal.exceptions import ApiError, ReplyStatus


class PresetAPI:
    """List / apply / reset presets."""

    def __init__(self, client):
        self._client = client

    def list(self, class_id: str = "") -> list:
        """
        List presets.

        Args:
            class_id: Optional category filter. If given, returns only the
                presets of that class. If empty, returns every class with its
                presets nested.

        Returns:
            When ``class_id`` is empty, a list of class dicts, each holding
            ``id`` (str, class ID), ``name`` (str, display name), ``isTeam``
            (bool), ``type`` (str, one of ``"system"`` / ``"user"`` /
            ``"team"`` / ``"unknown"``) and ``presets`` (list of preset
            dicts). When ``class_id`` is given, a flat list of preset dicts,
            each holding ``id`` (str, the suit ExtendId), ``name`` (str,
            display name), ``classId`` (str, owning class ID) and ``type``
            (str). Either list is empty when the host returns no data.

        Note:
            * A preset's ``id`` is the suit ExtendId; it is what
              :meth:`apply_to_image` expects as ``suit_id``. There is no
              separate ``suitId`` key in this response.
            * ``type`` on a class is one of :class:`~evoto.core.api_fields.PresetType`
              (``"system"`` / ``"user"`` / ``"team"`` / ``"unknown"``). Use it to
              tell recommended presets from user and team ones.
            * ``type`` on a preset is currently always an empty string, and
              ``isTeam`` on a class is currently always ``False``; neither is
              populated by the host. Do not branch on them - check the class
              ``type`` instead.
        """
        result = self._client.call(PresetCmd.LIST, {PresetField.CLASS_ID: class_id})
        if class_id:
            return result.get(PresetField.PRESETS, [])
        return result.get(PresetField.CLASSES, [])

    def find_by_name(self, name: str) -> list:
        """
        Look up presets by their display name.

        Convenience wrapper over :meth:`list`: it walks every class and
        collects the presets whose name matches exactly. Preset names are not
        unique across classes, so every match is returned and the owning class
        is reported alongside each one.

        Args:
            name: Exact preset name, case-sensitive, as shown in the host UI.

        Returns:
            A list of match dicts, one per preset carrying that name, each
            holding ``id`` (str, the suit ExtendId, pass it to
            :meth:`apply_to_image` as ``suit_id``), ``name`` (str, the matched
            preset name), ``classId`` (str, ID of the owning class),
            ``className`` (str, display name of the owning class) and
            ``classType`` (str, one of ``"system"`` / ``"user"`` / ``"team"``
            / ``"unknown"``). The list holds at least one entry; a single
            match means the name is unambiguous.

        Raises:
            ApiError: ``400`` when ``name`` is empty, ``404`` when no preset
                carries that name.

        Note:
            Preset suit IDs can change when presets are updated. Resolve the
            current ID by name close to the time of application instead of
            persisting an ID indefinitely. Names can exist in more than one
            class, so use ``classId`` or ``className`` to select the intended
            match when this method returns multiple entries.
        """
        if not name:
            raise ApiError(
                ApiErrorCode.BAD_REQUEST, "name must be a non-empty string"
            )

        matches = []
        for preset_class in self.list():
            for preset in preset_class.get(PresetField.PRESETS, []):
                if preset.get(Field.NAME) != name:
                    continue
                matches.append({
                    Field.ID: preset.get(Field.ID, ""),
                    Field.NAME: preset.get(Field.NAME, ""),
                    PresetField.CLASS_ID: preset_class.get(Field.ID, ""),
                    PresetField.CLASS_NAME: preset_class.get(Field.NAME, ""),
                    PresetField.CLASS_TYPE: preset_class.get(PresetField.TYPE, ""),
                })

        if not matches:
            raise ApiError(
                ApiErrorCode.NOT_FOUND, f"No preset named {name!r}"
            )
        return matches

    def apply_to_image(
        self,
        suit_id: str,
        imageIds: list[int],
        render: bool = True,
    ) -> dict:
        """Apply preset to specific images by image ID.

        This method targets the specified images directly, regardless of
        the current selection in the host application.

        Args:
            suit_id: The preset suit ExtendId.
            imageIds: List of image IDs.
            render: If True (default), trigger the rendering pipeline so
                the effect is visible immediately. If False, the effect is
                applied without immediately triggering render.

        Returns:
            ``{"success": True, "appliedCount": N}``

        Important:
            Preset updates can change the suit ID. Resolve the current
            ``suit_id`` with :meth:`find_by_name` before applying instead of
            relying on a long-lived stored ID. This synchronous method does
            not prepare missing preset details. Call :meth:`ensure_ready_async`
            first and wait for a successful callback before applying.
            Dispatch this blocking call back to the application or worker
            thread; do not invoke it directly on the SDK callback thread.
        """
        params = {
            PresetField.SUIT_ID: suit_id,
            PresetField.RENDER: render,
            PresetField.IMAGE_IDS: imageIds,
        }
        return self._client.call(PresetCmd.APPLY_TO_IMAGE, params)

    def apply_to_image_async(
        self,
        suit_id: str,
        imageIds: list[int],
        callback: Callable[[Any, ReplyStatus], None],
        timeout: float = 120.0,
    ) -> str:
        """Prepare and apply a preset without blocking the caller.

        The host verifies the suit ID, downloads missing preset details, and
        applies the preset before delivering the callback. Images in the
        current project are refreshed automatically; images outside the
        current project are updated without refreshing the current gallery.

        Args:
            suit_id: Current preset suit ExtendId to prepare and apply. Preset
                updates can change this ID; obtain the current value from
                :meth:`find_by_name`.
            imageIds: Image IDs that should receive the preset.
            callback: Called as ``callback(result, status)`` after the entire
                preparation and application workflow finishes. Do not assume
                that callbacks run on a fixed thread; see Callback delivery
                below.
            timeout: Maximum seconds to wait for the final reply.

        Returns:
            A string request ID returned immediately after the request is
            queued. The same value is available as ``status.request_id`` when
            the callback runs and can be passed to
            ``evoto.host.cancel_request``.

        Result payload:
            The callback receives ``result`` as a dict on success:

            * ``success`` (bool): Always ``True`` for a successful reply.
            * ``appliedCount`` (int): Number of images actually updated. This
              is ``0`` when none of the supplied image IDs resolve to an
              applicable image.
            * ``downloaded`` (bool): Whether this request downloaded missing
              preset details before applying the preset. ``False`` means the
              preset was already ready locally; it does not indicate failure.

            For a successful reply, ``status.is_success`` is ``True``,
            ``status.is_timeout`` is ``False``, ``status.error_code`` is ``0``,
            and ``status.error_message`` is empty.

        Error handling:
            For a host error, ``result`` is ``None``, ``status.is_success``
            and ``status.is_timeout`` are ``False``, and
            ``status.error_code`` / ``status.error_message`` describe the
            error. An unknown or stale ``suit_id`` is reported with error code
            ``404``. For a timeout, ``result`` is ``None``,
            ``status.is_success`` is ``False``, and ``status.is_timeout`` is
            ``True``. ``status.elapsed_ms`` reports the time until completion
            or timeout in both cases.

        Callback delivery:
            Successful host replies and host errors usually invoke the
            callback on the SDK receiver thread. Timeouts invoke it on the SDK
            timer thread. A local send failure invokes it immediately on the
            thread calling this method, potentially before this method
            returns. Marshal to the appropriate application thread before
            touching thread-affine state such as GUI objects.

        Important:
            Preset updates can change the suit ID. Resolve the current
            ``suit_id`` with :meth:`find_by_name` close to the time of
            application instead of relying on a long-lived stored ID. This
            method automatically downloads missing preset details before
            applying.

        Cancellation:
            If ``evoto.host.cancel_request(request_id)`` returns ``True``, the
            callback runs locally with ``result`` set to ``None``,
            ``status.is_success`` and ``status.is_timeout`` set to ``False``,
            and cancellation described by ``status.error_message``. The
            callback runs synchronously on the thread calling
            ``cancel_request``. A later host reply is ignored. Cancellation
            does not stop host-side download or application.
        """
        params = {
            PresetField.SUIT_ID: suit_id,
            PresetField.IMAGE_IDS: imageIds,
        }
        return self._client.call_async(
            PresetCmd.APPLY_TO_IMAGE_ASYNC,
            params,
            callback,
            timeout,
        )

    def reset(
        self,
        imageIds: list[int],
        render: bool = True,
    ) -> dict:
        """Reset preset effect for specified images.

        Args:
            imageIds: List of image IDs to reset.
            render: Trigger rendering pipeline (default True).

        Returns:
            ``{"success": True, "appliedCount": N}``
        """
        params = {
            PresetField.IMAGE_IDS: imageIds,
            PresetField.RENDER: render,
        }
        return self._client.call(PresetCmd.RESET, params)

    def ensure_ready_async(
        self,
        suit_ids: list[str],
        callback: Callable[[Any, ReplyStatus], None],
        timeout: float = 120.0,
    ) -> str:
        """Ensure preset suits are downloaded and ready before later use.

        Args:
            suit_ids: Current preset suit IDs to resolve on the host. Preset
                updates can change these IDs; obtain current values from
                :meth:`find_by_name` instead of relying on long-lived stored
                values. Pass suit IDs only, not beautify or palette preset
                IDs.
            callback: Called as ``callback(result, status)`` when the request
                finishes. Do not assume that callbacks run on a fixed thread;
                see Callback delivery below.
            timeout: Maximum seconds to wait before the request times out.

        Returns:
            A string request ID returned immediately after the request is
            queued. The same value is available as ``status.request_id`` when
            the callback runs and can be passed to
            ``evoto.host.cancel_request``.

        Result payload:
            The callback receives ``result`` as a dict on success:

            * ``success`` (bool): Always ``True`` for a successful reply.
            * ``readySuitIds`` (list[str]): Every requested suit ID confirmed
              ready after local validation and any required download.
            * ``downloaded`` (bool): Whether this request downloaded missing
              preset details. ``False`` means every requested suit was already
              ready locally; it does not indicate failure.

            For a successful reply, ``status.is_success`` is ``True``,
            ``status.is_timeout`` is ``False``, ``status.error_code`` is ``0``,
            and ``status.error_message`` is empty.

        Error handling:
            For a host error, ``result`` is ``None``, ``status.is_success``
            and ``status.is_timeout`` are ``False``, and
            ``status.error_code`` / ``status.error_message`` describe the
            error. An unknown or stale suit ID is reported with error code
            ``404``. For a timeout, ``result`` is ``None``,
            ``status.is_success`` is ``False``, and ``status.is_timeout`` is
            ``True``. ``status.elapsed_ms`` reports the time until completion
            or timeout in both cases.

        Callback delivery:
            Successful host replies and host errors usually invoke the
            callback on the SDK receiver thread. Timeouts invoke it on the SDK
            timer thread. A local send failure invokes it immediately on the
            thread calling this method, potentially before this method
            returns. Marshal to the appropriate application thread before
            touching thread-affine state such as GUI objects.

        Cancellation:
            If ``evoto.host.cancel_request(request_id)`` returns ``True``, the
            callback runs locally with ``result`` set to ``None``,
            ``status.is_success`` and ``status.is_timeout`` set to ``False``,
            and cancellation described by ``status.error_message``. The
            callback runs synchronously on the thread calling
            ``cancel_request``. A later host reply is ignored. Cancellation
            does not stop an in-progress host download or host-side preset
            preparation.
        """
        return self._client.call_async(
            PresetCmd.ENSURE_READY,
            {PresetField.SUIT_IDS: suit_ids},
            callback,
            timeout,
        )
