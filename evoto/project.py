"""Project-related host RPC wrappers."""

from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from .core.api_commands import ProjectCmd
from .core.api_fields import Field, ProjectField

if TYPE_CHECKING:
    from .core._client import Client


class ProjectAPI:
    """Pythonic helpers around ``project.*`` host commands."""

    def __init__(self, client: "Client") -> None:
        """
        Args:
            client: Internal SDK client (``evoto.core._client._instance``).
        """
        self._client = client

    def create(
        self,
        name: str,
        group_id: int | None = 0,
        *,
        data_mode: bool = False,
        use_current_group: bool = False,
        allow_cross_cloud_sync: bool = False,
    ) -> dict:
        """
        Create a project.

        Args:
            name: Display name.
            group_id: Parent folder id.
            data_mode: Use a background-safe path that does not depend on the
                currently open UI state.
            use_current_group: When true, ask the host to use the currently selected group.
            allow_cross_cloud_sync: When true, create the project with cross-cloud sync enabled.

        Returns:
            Created project payload from host.
        """
        payload = {Field.NAME: name}
        if use_current_group:
            payload[ProjectField.USE_CURRENT_GROUP] = True
        elif group_id is not None:
            payload[ProjectField.GROUP_ID] = group_id
        if allow_cross_cloud_sync:
            payload[ProjectField.ALLOW_CROSS_CLOUD_SYNC] = True
        if data_mode:
            payload[ProjectField.DATA_MODE] = True
        return self._client.call(ProjectCmd.CREATE, payload)

    def list(
        self,
        group_id: int | None = None,
        *,
        include_disabled: bool = False,
        data_mode: bool = False,
        use_current_group: bool = False,
    ) -> list:
        """
        List projects.

        The host currently returns the full project list for the resolved
        group; pagination is not supported at the RPC layer.

        Args:
            group_id: Filter by folder.
            include_disabled: Include deleted/disabled projects when supported.
            data_mode: Use a background-safe path that does not depend on the
                currently open UI state.
            use_current_group: When true, ask the host to use the currently selected group.

        Returns:
            List of project dicts.
        """
        payload: dict = {}
        if use_current_group:
            payload[ProjectField.USE_CURRENT_GROUP] = True
        elif group_id is not None:
            payload[ProjectField.GROUP_ID] = group_id
        if include_disabled:
            payload[ProjectField.INCLUDE_DISABLED] = True
        if data_mode:
            payload[ProjectField.DATA_MODE] = True
        result = self._client.call(ProjectCmd.LIST, payload)
        return result.get(ProjectField.PROJECTS, [])

    def current(self) -> dict:
        """Get the currently active project in the host image library.

        Returns:
            Project detail dict (same shape as :meth:`info`).

        Raises:
            ApiError: 404 if no project is open.
        """
        return self._client.call(ProjectCmd.CURRENT, {})

    def switch(self, project_id: int) -> dict:
        """Switch the host UI to a project.

        The host first returns to the library page when needed. If a modal
        dialog or popup is open, the host rejects the request and does not
        switch projects. The call returns ``status="pending"`` after the host
        accepts the request. Listen to ``project.switch.completed`` or
        ``project.switch.failed`` for the final result.

        Args:
            project_id: Project ID to switch to.

        Returns:
            Host response with ``success``, ``status`` and the target project
            payload.
        """
        return self._client.call(ProjectCmd.SWITCH, {ProjectField.PROJECT_ID: project_id})

    def convert_to_cloud(
        self,
        project_id: int,
        *,
        team_id: int | None = None,
        storage_path: str | None = None,
    ) -> dict:
        """Convert a local project into a cloud-synced project.

        The host returns when the conversion request is accepted. The project
        becomes a cloud project asynchronously; listen to
        ``project.convertToCloud.completed`` or
        ``project.convertToCloud.failed`` for the final result.

        Args:
            project_id: Local project ID to convert.
            team_id: Target team or cloud space ID. Omit to use the host's
                current cloud space.
            storage_path: Optional storage path for compatible cloud storage
                providers.

        Returns:
            Host response with ``accepted``, ``status`` and ``project_id``.
        """
        payload = {ProjectField.PROJECT_ID: project_id}
        if team_id is not None:
            payload[ProjectField.TEAM_ID] = team_id
        if storage_path:
            payload[ProjectField.STORAGE_PATH] = storage_path
        return self._client.call(ProjectCmd.CONVERT_TO_CLOUD, payload)

    def stop_cloud_loading(self, project_id: int) -> dict:
        """Stop loading/downloading a cloud project by ID.

        Use this when a cloud project takes too long to load and you want to
        cancel the in-progress loading instead of waiting.

        Args:
            project_id: Cloud project ID whose loading should be stopped.

        Returns:
            Host response with ``success``, ``stopped`` and ``project_id``.
            ``stopped`` is ``True`` for a cloud project (the stop request is
            accepted regardless of whether a download is actually in progress),
            and ``False`` for a local project, which has no cloud loading to
            stop.
        """
        return self._client.call(
            ProjectCmd.STOP_CLOUD_LOADING, {ProjectField.PROJECT_ID: project_id}
        )

    def cloud_status(self, project_id: int) -> dict:
        """Return current cloud upload/download status for a project.

        The payload includes ``project_id``, ``status``, ``upload_progress``,
        and ``download_progress``. ``status`` is ``uploading``, ``downloading``,
        or ``idle``. Historical completed/failed/paused states are not included;
        subscribe to cloud events to receive those notifications.

        Args:
            project_id: Project ID to inspect.

        Returns:
            Current active transfer status payload.
        """
        return self._client.call(
            ProjectCmd.CLOUD_STATUS, {ProjectField.PROJECT_ID: project_id}
        )

    def info(
        self,
        project_id: int | None = None,
        *,
        data_mode: bool = False,
        use_current_project: bool = False,
    ) -> dict:
        """
        Get a single project by id.

        Args:
            project_id: Project identifier.
            data_mode: Use a background-safe path that does not depend on the
                currently open UI state.
            use_current_project: When true, ask the host to use the currently active project.

        Returns:
            Project detail dict.
        """
        payload = {}
        if use_current_project:
            payload[ProjectField.USE_CURRENT_PROJECT] = True
        elif project_id is not None:
            payload[ProjectField.PROJECT_ID] = project_id
        if data_mode:
            payload[ProjectField.DATA_MODE] = True
        return self._client.call(ProjectCmd.INFO, payload)

    def rename(
        self,
        project_id: int | None,
        name: str,
        *,
        data_mode: bool = False,
        use_current_project: bool = False,
    ) -> dict:
        """
        Rename a project.

        Args:
            project_id: Project identifier.
            name: New display name.
            data_mode: Use a background-safe path that does not depend on the
                currently open UI state.
            use_current_project: When true, ask the host to use the currently active project.

        Returns:
            Updated project payload from host.
        """
        payload = {Field.NAME: name}
        if use_current_project:
            payload[ProjectField.USE_CURRENT_PROJECT] = True
        elif project_id is not None:
            payload[ProjectField.PROJECT_ID] = project_id
        if data_mode:
            payload[ProjectField.DATA_MODE] = True
        return self._client.call(ProjectCmd.RENAME, payload)

    def delete(
        self,
        project_id: int | None = None,
        *,
        data_mode: bool = False,
        use_current_project: bool = False,
    ) -> dict:
        """Move a project to the recycle bin.

        Args:
            project_id: Project ID to delete. Ignored when
                ``use_current_project`` is true.
            data_mode: Use a background-safe path that does not depend on the
                currently open UI state.
            use_current_project: Delete the currently selected project in the
                host.

        Returns:
            ``{"success": True}`` when the request is accepted.
        """
        payload = {}
        if use_current_project:
            payload[ProjectField.USE_CURRENT_PROJECT] = True
        elif project_id is not None:
            payload[ProjectField.PROJECT_ID] = project_id
        if data_mode:
            payload[ProjectField.DATA_MODE] = True
        return self._client.call(ProjectCmd.DELETE, payload)

    def group_list(self, *, data_mode: bool = False) -> list:
        """List all project groups.

        Args:
            data_mode: Use a background-safe path that does not depend on the
                currently open UI state.

        Returns:
            List of project group dicts.
        """
        payload = {}
        if data_mode:
            payload[ProjectField.DATA_MODE] = True
        result = self._client.call(ProjectCmd.GROUP_LIST, payload)
        return result.get(ProjectField.GROUPS, [])

    def group_get(
        self,
        group_id: int | None = None,
        *,
        data_mode: bool = False,
        use_current_group: bool = False,
    ) -> dict:
        """Get a single project group by ID or current selection.

        Args:
            group_id: Project group ID to query. Ignored when
                ``use_current_group`` is true.
            data_mode: Use a background-safe path that does not depend on the
                currently open UI state.
            use_current_group: Prefer the currently selected project group in
                the host.

        Returns:
            Project group detail dict.
        """
        payload = {}
        if use_current_group:
            payload[ProjectField.USE_CURRENT_GROUP] = True
        elif group_id is not None:
            payload[ProjectField.GROUP_ID] = group_id
        if data_mode:
            payload[ProjectField.DATA_MODE] = True
        return self._client.call(ProjectCmd.GROUP_GET, payload)

    def group_create(self, name: str, *, data_mode: bool = False) -> dict:
        """Create a project group.

        Args:
            name: Display name for the new project group.
            data_mode: Use a background-safe path that does not depend on the
                currently open UI state.

        Returns:
            Created project group payload from host.
        """
        payload = {Field.NAME: name}
        if data_mode:
            payload[ProjectField.DATA_MODE] = True
        return self._client.call(ProjectCmd.GROUP_CREATE, payload)

    def group_rename(
        self,
        group_id: int | None,
        name: str,
        *,
        data_mode: bool = False,
        use_current_group: bool = False,
    ) -> dict:
        """Rename a project group by ID or current selection.

        Args:
            group_id: Project group ID to rename. Ignored when
                ``use_current_group`` is true.
            name: New display name.
            data_mode: Use a background-safe path that does not depend on the
                currently open UI state.
            use_current_group: Rename the currently selected project group in
                the host.

        Returns:
            Updated project group payload from host.
        """
        payload = {Field.NAME: name}
        if use_current_group:
            payload[ProjectField.USE_CURRENT_GROUP] = True
        elif group_id is not None:
            payload[ProjectField.GROUP_ID] = group_id
        if data_mode:
            payload[ProjectField.DATA_MODE] = True
        return self._client.call(ProjectCmd.GROUP_RENAME, payload)

    def group_delete(
        self,
        group_id: int | None = None,
        *,
        data_mode: bool = False,
        use_current_group: bool = False,
    ) -> dict:
        """Delete a project group by ID or current selection.

        Args:
            group_id: Project group ID to delete. Ignored when
                ``use_current_group`` is true.
            data_mode: Use a background-safe path that does not depend on the
                currently open UI state.
            use_current_group: Delete the currently selected project group in
                the host.

        Returns:
            ``{"success": True}`` when the request is accepted.
        """
        payload = {}
        if use_current_group:
            payload[ProjectField.USE_CURRENT_GROUP] = True
        elif group_id is not None:
            payload[ProjectField.GROUP_ID] = group_id
        if data_mode:
            payload[ProjectField.DATA_MODE] = True
        return self._client.call(ProjectCmd.GROUP_DELETE, payload)

    # ---- Lifecycle events ----------------------------------------------
    # The host pushes project/group create/rename/delete events to every
    # subscribed plugin; the SDK performs the host.subscribe handshake
    # automatically the first time you attach a listener.
    #
    # IMPORTANT - all ``on_*`` callbacks run on the SDK's ``evoto-event``
    # thread, NOT on your GUI main thread. See :py:meth:`evoto.core._client.Client.on`
    # for the full threading contract. Short version:
    #
    #   * Safe to call host RPCs (``evoto.project.list()``) from inside.
    #   * NOT safe to touch Qt/Tk widgets - marshal via a queued signal.
    #   * Keep callbacks short; long work delays the next event.
    #
    # Canonical Qt pattern (see :py:meth:`on_changed` for the full
    # example; simpler ``on_created`` / ``on_deleted`` etc. follow the
    # same rule).

    def on_created(self, callback: Callable[[dict], None]) -> None:
        """Fired after a project is created. Payload is the project dict.

        Callback runs on the ``evoto-event`` thread - see
        :py:meth:`on_changed` for the Qt-safe pattern.

        Args:
            callback: Function called with the created project payload.
        """
        self._client.on(ProjectCmd.CREATED_EVENT, callback)

    def on_renamed(self, callback: Callable[[dict], None]) -> None:
        """Fired after a project is renamed. Payload is the project dict.

        See :py:meth:`on_changed` for the threading contract.

        Args:
            callback: Function called with the renamed project payload.
        """
        self._client.on(ProjectCmd.RENAMED_EVENT, callback)

    def on_deleted(self, callback: Callable[[dict], None]) -> None:
        """Fired after a project is moved to recycle bin.

        Payload carries ``project_id``.

        See :py:meth:`on_changed` for the threading contract.

        Args:
            callback: Function called with the deleted project payload.
        """
        self._client.on(ProjectCmd.DELETED_EVENT, callback)

    def on_switch_completed(self, callback: Callable[[dict], None]) -> None:
        """Fired after ``project.switch`` makes the target project active.

        Payload includes ``project_id`` and the target ``project`` object.

        Args:
            callback: Function called with the completed payload.
        """
        self._client.on(ProjectCmd.SWITCH_COMPLETED, callback)

    def on_switch_failed(self, callback: Callable[[dict], None]) -> None:
        """Fired when ``project.switch`` fails after being accepted.

        Payload includes ``project_id`` and failure ``message``.

        Args:
            callback: Function called with the failure payload.
        """
        self._client.on(ProjectCmd.SWITCH_FAILED, callback)

    def on_convert_to_cloud_completed(self, callback: Callable[[dict], None]) -> None:
        """Fired after a local project is converted to a cloud project. Payload
        includes ``project_id``, ``team_id``, ``success`` of ``True``,
        ``status`` of ``completed`` and the updated ``project`` object when
        available; no ``message`` field.

        Args:
            callback: Function called with the completed payload.
        """
        self._client.on(ProjectCmd.CONVERT_TO_CLOUD_COMPLETED, callback)

    def on_convert_to_cloud_failed(self, callback: Callable[[dict], None]) -> None:
        """Fired when a project cloud conversion fails. Payload includes
        ``project_id``, ``team_id``, ``success`` of ``False``, ``status`` of
        ``failed``, a language-neutral English ``message``,
        ``internal_error_code``, ``local_error_code`` and ``debug_code`` when
        the host provides them.

        Args:
            callback: Function called with the failure payload.
        """
        self._client.on(ProjectCmd.CONVERT_TO_CLOUD_FAILED, callback)

    def on_cloud_upload_completed(self, callback: Callable[[dict], None]) -> None:
        """Fired after all images in a cloud project finish uploading. Payload
        includes ``project_id``, ``success`` of ``True``, ``status`` of
        ``completed``, ``upload_progress`` of 100 and the ``project`` object
        when available; successful events carry no ``message`` field.

        Args:
            callback: Function called with the completed payload.
        """
        self._client.on(ProjectCmd.CLOUD_UPLOAD_COMPLETED, callback)

    def on_cloud_upload_failed(self, callback: Callable[[dict], None]) -> None:
        """Fired when project image upload pauses or fails after cloud
        conversion. Payload includes ``project_id``, ``success`` of ``False``,
        ``status`` of ``failed``, a language-neutral English ``message`` and
        ``internal_error_code`` (plus ``local_error_code`` and ``debug_code``
        when the host provides them).

        Args:
            callback: Function called with the failure payload.
        """
        self._client.on(ProjectCmd.CLOUD_UPLOAD_FAILED, callback)

    def on_cloud_upload_progress(self, callback: Callable[[dict], None]) -> None:
        """Fired when project image upload progress changes. Payload includes
        ``project_id``, ``status`` of ``uploading`` and ``upload_progress``
        (0-100).

        Args:
            callback: Function called with the progress payload.
        """
        self._client.on(ProjectCmd.CLOUD_UPLOAD_PROGRESS, callback)

    def on_cloud_download_progress(self, callback: Callable[[dict], None]) -> None:
        """Fired when cloud project download progress changes. Payload includes
        ``project_id``, ``status`` of ``downloading`` and ``download_progress``
        (0-100).

        Args:
            callback: Function called with the progress payload.
        """
        self._client.on(ProjectCmd.CLOUD_DOWNLOAD_PROGRESS, callback)

    def on_cloud_download_completed(self, callback: Callable[[dict], None]) -> None:
        """Fired after cloud project image download finishes successfully.
        Payload includes ``project_id``, ``success`` of ``True``, ``status`` of
        ``completed``, ``download_progress`` of 100 and the error-code fields
        (``internal_error_code``, ``local_error_code``, ``debug_code``) set to
        ``-1``; successful events carry no ``message`` field.

        Args:
            callback: Function called with the completed payload.
        """
        self._client.on(ProjectCmd.CLOUD_DOWNLOAD_COMPLETED, callback)

    def on_cloud_download_failed(self, callback: Callable[[dict], None]) -> None:
        """Fired when cloud project image download fails. Payload includes
        ``project_id``, ``success`` of ``False``, ``status`` of ``failed``,
        ``download_progress`` of 0, a language-neutral English ``message``,
        ``internal_error_code``, ``local_error_code`` and ``debug_code`` when
        available.

        Args:
            callback: Function called with the failure payload.
        """
        self._client.on(ProjectCmd.CLOUD_DOWNLOAD_FAILED, callback)

    def on_cloud_download_paused(self, callback: Callable[[dict], None]) -> None:
        """Fired when cloud project image download is paused by the host.
        Payload includes ``project_id``, ``success`` of ``False``, ``status`` of
        ``paused`` and a language-neutral English ``message``.

        Args:
            callback: Function called with the paused payload.
        """
        self._client.on(ProjectCmd.CLOUD_DOWNLOAD_PAUSED, callback)

    def on_cloud_image_upload_failed(self, callback: Callable[[dict], None]) -> None:
        """Fired when a single cloud image upload fails. Payload includes
        ``project_id``, ``file_id``, ``success`` of ``False``, ``status``, a
        language-neutral English ``message``, ``internal_error_code``,
        ``local_error_code`` and ``debug_code``.

        Args:
            callback: Function called with the failure payload.
        """
        self._client.on(ProjectCmd.CLOUD_IMAGE_UPLOAD_FAILED, callback)

    def on_cloud_image_download_failed(self, callback: Callable[[dict], None]) -> None:
        """Fired when a single cloud image download fails. Payload includes
        ``project_id``, ``file_id``, ``download_type``, ``success`` of
        ``False``, ``status``, a language-neutral English ``message``,
        ``internal_error_code``, ``local_error_code`` and ``debug_code``.

        Args:
            callback: Function called with the failure payload.
        """
        self._client.on(ProjectCmd.CLOUD_IMAGE_DOWNLOAD_FAILED, callback)

    def on_group_created(self, callback: Callable[[dict], None]) -> None:
        """Fired after a project group is created.

        See :py:meth:`on_changed` for the threading contract.

        Args:
            callback: Function called with the created group payload.
        """
        self._client.on(ProjectCmd.GROUP_CREATED_EVENT, callback)

    def on_group_renamed(self, callback: Callable[[dict], None]) -> None:
        """Fired after a project group is renamed.

        See :py:meth:`on_changed` for the threading contract.

        Args:
            callback: Function called with the renamed group payload.
        """
        self._client.on(ProjectCmd.GROUP_RENAMED_EVENT, callback)

    def on_group_deleted(self, callback: Callable[[dict], None]) -> None:
        """Fired after a project group is removed.

        See :py:meth:`on_changed` for the threading contract.

        Args:
            callback: Function called with the deleted group payload.
        """
        self._client.on(ProjectCmd.GROUP_DELETED_EVENT, callback)

    def on_changed(self, callback: Callable[[str, dict], None]) -> Callable[[], None]:
        """Subscribe to every project & group lifecycle event at once.

        ``callback(event_name, data)`` fires whenever the host notifies a
        create / rename / delete / convert-to-cloud on projects, or create /
        rename / delete on groups. Convenient
        for UIs that simply refresh a whole tree on any change.

        **Threading**
            The callback runs on the SDK's ``evoto-event`` thread - same
            contract as :py:meth:`evoto.core._client.Client.on`. Safe to
            call synchronous host RPCs; unsafe to touch widgets directly.

        **Qt pattern (copy-paste)**::

            from PySide6.QtCore import Signal
            from PySide6.QtWidgets import QMainWindow
            import evoto

            class Window(QMainWindow):
                changed = Signal(str, object)   # event_name, payload

                def __init__(self):
                    super().__init__()
                    # Queued connection: slot runs on the GUI main thread.
                    self.changed.connect(self._on_change)
                    # SDK thread emits; Qt delivers the signal on GUI thread.
                    self._dispose = evoto.project.on_changed(
                        lambda name, data: self.changed.emit(name, data)
                    )

                def _on_change(self, name, data):
                    self.refresh_tree()             # safe - GUI thread here

                def closeEvent(self, event):
                    self._dispose()                 # unsubscribe cleanly
                    super().closeEvent(event)

        Returns:
            A zero-arg disposer that unregisters every listener installed
            by this call. Hold onto it if you want to detach later.

        Args:
            callback: Function called as ``callback(event_name, payload)``.
        """
        installed: list[tuple[str, Callable[[dict], None]]] = []
        for event_name in ProjectCmd.LIFECYCLE_EVENTS:
            def trampoline(data, _name=event_name):
                callback(_name, data)
            self._client.on(event_name, trampoline)
            installed.append((event_name, trampoline))

        def _dispose() -> None:
            for name, cb in installed:
                self._client.off(name, cb)

        return _dispose

    def off_created(self, callback: Callable | None = None) -> None:
        """Unregister ``project.created`` listeners.

        Args:
            callback: Callback to remove. Omit to remove all created-event
                callbacks registered by this client.
        """
        self._client.off(ProjectCmd.CREATED_EVENT, callback)

    def off_renamed(self, callback: Callable | None = None) -> None:
        """Unregister ``project.renamed`` listeners.

        Args:
            callback: Callback to remove. Omit to remove all renamed-event
                callbacks registered by this client.
        """
        self._client.off(ProjectCmd.RENAMED_EVENT, callback)

    def off_deleted(self, callback: Callable | None = None) -> None:
        """Unregister ``project.deleted`` listeners.

        Args:
            callback: Callback to remove. Omit to remove all deleted-event
                callbacks registered by this client.
        """
        self._client.off(ProjectCmd.DELETED_EVENT, callback)

    def off_switch_completed(self, callback: Callable | None = None) -> None:
        """Unregister ``project.switch.completed`` listeners.

        Args:
            callback: Callback to remove. Omit to remove all switch completion
                callbacks registered by this client.
        """
        self._client.off(ProjectCmd.SWITCH_COMPLETED, callback)

    def off_switch_failed(self, callback: Callable | None = None) -> None:
        """Unregister ``project.switch.failed`` listeners.

        Args:
            callback: Callback to remove. Omit to remove all switch failure
                callbacks registered by this client.
        """
        self._client.off(ProjectCmd.SWITCH_FAILED, callback)

    def off_convert_to_cloud_completed(self, callback: Callable | None = None) -> None:
        """Unregister ``project.convertToCloud.completed`` listeners.

        Args:
            callback: Callback to remove. Omit to remove all conversion
                completion callbacks registered by this client.
        """
        self._client.off(ProjectCmd.CONVERT_TO_CLOUD_COMPLETED, callback)

    def off_convert_to_cloud_failed(self, callback: Callable | None = None) -> None:
        """Unregister ``project.convertToCloud.failed`` listeners.

        Args:
            callback: Callback to remove. Omit to remove all conversion
                failure callbacks registered by this client.
        """
        self._client.off(ProjectCmd.CONVERT_TO_CLOUD_FAILED, callback)

    def off_cloud_upload_completed(self, callback: Callable | None = None) -> None:
        """Unregister ``project.cloudUpload.completed`` listeners.

        Args:
            callback: Callback to remove. Omit to remove all upload completion
                callbacks registered by this client.
        """
        self._client.off(ProjectCmd.CLOUD_UPLOAD_COMPLETED, callback)

    def off_cloud_upload_failed(self, callback: Callable | None = None) -> None:
        """Unregister ``project.cloudUpload.failed`` listeners.

        Args:
            callback: Callback to remove. Omit to remove all upload failure
                callbacks registered by this client.
        """
        self._client.off(ProjectCmd.CLOUD_UPLOAD_FAILED, callback)

    def off_cloud_upload_progress(self, callback: Callable | None = None) -> None:
        """Unregister ``project.cloudUpload.progress`` listeners."""
        self._client.off(ProjectCmd.CLOUD_UPLOAD_PROGRESS, callback)

    def off_cloud_download_progress(self, callback: Callable | None = None) -> None:
        """Unregister ``project.cloudDownload.progress`` listeners."""
        self._client.off(ProjectCmd.CLOUD_DOWNLOAD_PROGRESS, callback)

    def off_cloud_download_completed(self, callback: Callable | None = None) -> None:
        """Unregister ``project.cloudDownload.completed`` listeners."""
        self._client.off(ProjectCmd.CLOUD_DOWNLOAD_COMPLETED, callback)

    def off_cloud_download_failed(self, callback: Callable | None = None) -> None:
        """Unregister ``project.cloudDownload.failed`` listeners."""
        self._client.off(ProjectCmd.CLOUD_DOWNLOAD_FAILED, callback)

    def off_cloud_download_paused(self, callback: Callable | None = None) -> None:
        """Unregister ``project.cloudDownload.paused`` listeners."""
        self._client.off(ProjectCmd.CLOUD_DOWNLOAD_PAUSED, callback)

    def off_cloud_image_upload_failed(self, callback: Callable | None = None) -> None:
        """Unregister ``project.cloudImageUpload.failed`` listeners."""
        self._client.off(ProjectCmd.CLOUD_IMAGE_UPLOAD_FAILED, callback)

    def off_cloud_image_download_failed(self, callback: Callable | None = None) -> None:
        """Unregister ``project.cloudImageDownload.failed`` listeners."""
        self._client.off(ProjectCmd.CLOUD_IMAGE_DOWNLOAD_FAILED, callback)

    def off_group_created(self, callback: Callable | None = None) -> None:
        """Unregister ``project.group.created`` listeners.

        Args:
            callback: Callback to remove. Omit to remove all group-created
                callbacks registered by this client.
        """
        self._client.off(ProjectCmd.GROUP_CREATED_EVENT, callback)

    def off_group_renamed(self, callback: Callable | None = None) -> None:
        """Unregister ``project.group.renamed`` listeners.

        Args:
            callback: Callback to remove. Omit to remove all group-renamed
                callbacks registered by this client.
        """
        self._client.off(ProjectCmd.GROUP_RENAMED_EVENT, callback)

    def off_group_deleted(self, callback: Callable | None = None) -> None:
        """Unregister ``project.group.deleted`` listeners.

        Args:
            callback: Callback to remove. Omit to remove all group-deleted
                callbacks registered by this client.
        """
        self._client.off(ProjectCmd.GROUP_DELETED_EVENT, callback)
