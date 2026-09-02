"""Project & Image Explorer - two-level tree (Group > Project) with image list.

Demonstrates all ProjectAPI and ImageAPI operations via the high-level SDK:
- Group CRUD (list / create / rename / delete)
- Project CRUD (list / create / rename / delete / info / current / switch / convert to cloud)
- Cloud project status query and upload/download event logging
- Image list / info / import / delete with event subscription
"""

import logging
import sys
from pathlib import Path
from pprint import pformat

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout,
    QInputDialog, QLabel, QMenu, QPushButton, QSplitter,
    QTextEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

import evoto
from demo.shared import (
    apply_theme, themed_confirm, themed_message,
    ConnectBar, ImageTable,
)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger('project_image_demo')

ROLE_ID = Qt.UserRole
ROLE_TYPE = Qt.UserRole + 1
ROLE_IS_CLOUD = Qt.UserRole + 2
NODE_GROUP = 'group'
NODE_PROJECT = 'project'

MY_IMPORT_LISTENER_UUID = 'project-image-demo-listener-001'

MENU_QSS = """
QMenu {
    background: #232629;
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 6px;
    padding: 4px 0;
    color: #f3f0e8;
    font-size: 12px;
}
QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
    margin: 1px 4px;
}
QMenu::item:selected {
    background: rgba(255, 255, 255, 0.08);
}
QMenu::separator {
    height: 1px;
    background: rgba(255, 255, 255, 0.07);
    margin: 4px 8px;
}
QMenu::item:disabled {
    color: rgba(243, 240, 232, 0.30);
}
"""


class ProjectImageDemoWindow(QWidget):
    # ---- Event callback pattern (blueprint for GUI plugins) -----------------
    # Every `evoto.*.on_*` callback runs on the SDK's dedicated
    # `evoto-event` thread, NOT on the Qt main thread. Touching widgets
    # from there will crash.
    #
    # The canonical fix is the three signals below: the SDK callbacks do
    # nothing except `.emit(...)`; Qt delivers each signal on the GUI
    # main thread via its default queued connection, where the matching
    # slot is free to rebuild the tree, enable buttons, append to the
    # log, etc.
    #
    # Copy this pattern for your own GUI plugin - or see the README
    # section "Handling Events Safely" for the full contract.
    event_received = Signal(str, object)      # import.* (SDK thread -> GUI)
    log_received = Signal(str)                # host log line (SDK thread -> GUI)
    lifecycle_received = Signal(str, object)  # project/group lifecycle

    def __init__(self):
        super().__init__()
        self._current_project_id: int | None = None
        self._current_project_name: str = ''

        self.event_received.connect(self._on_import_event)
        self.log_received.connect(self._append_log)
        self.lifecycle_received.connect(self._on_project_lifecycle)
        self._register_import_events()
        self._register_lifecycle_events()
        self._init_ui()
        apply_theme(self)

    def _register_import_events(self):
        for evt in ('import.started', 'import.progress',
                    'import.completed', 'import.failed'):
            evoto.on(evt, lambda data, e=evt: self.event_received.emit(e, data))

    def _register_lifecycle_events(self):
        """Subscribe to project / group lifecycle events.

        ``evoto.project.on_changed`` transparently issues a
        ``host.subscribe`` and fans out ``project.created`` /
        ``project.renamed`` / ``project.deleted`` (and the group
        counterparts) here. The callback runs on the SDK event thread,
        so we only ``emit`` - the Qt slot does the actual tree rebuild
        on the GUI thread.
        """
        evoto.project.on_changed(
            lambda event_name, data: self.lifecycle_received.emit(event_name, data)
        )
        evoto.project.on_convert_to_cloud_failed(
            lambda data: self.lifecycle_received.emit('project.convertToCloud.failed', data)
        )

    def _on_project_lifecycle(self, event_name: str, data: object):
        """Refresh the tree whenever the host reports a project/group change."""
        self._log(f'Host event: {event_name}')
        if event_name.startswith('project.convertToCloud.'):
            self._log(f'Convert to cloud event payload:\n{pformat(data)}')
        if event_name.startswith('project.cloudUpload.'):
            self._log(f'Cloud upload event payload:\n{pformat(data)}')
            # Upload progress/result does not change the project tree structure;
            # skip the tree refresh to avoid re-triggering host upload checks.
            return
        if event_name.startswith('project.cloudDownload.'):
            self._log(f'Cloud download event payload:\n{pformat(data)}')
            return
        if event_name.startswith('project.cloudImage'):
            self._log(f'Cloud image event payload:\n{pformat(data)}')
            return
        if event_name == 'project.switch.completed' and isinstance(data, dict):
            project = data.get('project', {})
            project_id = project.get('id') or data.get('project_id')
            name = project.get('name', '')
            if project_id:
                self._current_project_id = int(project_id)
                self._current_project_name = name
                self.current_project_label.setText(f'Current: {name} (ID: {project_id})')
                self._refresh_images()
        elif event_name == 'project.switch.failed':
            self._log(f'Project switch failed payload:\n{pformat(data)}')
        if not getattr(self, 'btn_refresh_tree', None) or not self.btn_refresh_tree.isEnabled():
            # Tree controls disabled before first connect - skip to avoid
            # spurious RPCs during startup.
            return
        self._refresh_tree()

    # ------------------------------------------------------------------ UI --

    def _init_ui(self):
        self.setWindowTitle('Project & Image Explorer')
        self.resize(1200, 780)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self.connect_bar = ConnectBar(title='Project & Image Explorer')
        self.connect_bar.connected.connect(self._on_connected)
        self.connect_bar.disconnected.connect(self._on_disconnected)
        self.connect_bar.connection_failed.connect(self._on_connect_failed)
        root.addWidget(self.connect_bar)

        body_splitter = QSplitter(Qt.Horizontal)

        body_splitter.addWidget(self._build_tree_panel())
        body_splitter.addWidget(self._build_image_panel())
        body_splitter.setSizes([340, 640])
        root.addWidget(body_splitter, 1)

        root.addWidget(self._build_log_panel(), 0)

    # -- Left: project tree --

    def _build_tree_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName('panelCard')
        frame.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        head = QHBoxLayout()
        title = QLabel('PROJECTS')
        title.setProperty('ev_role', 'section-title')
        head.addWidget(title)
        head.addStretch()

        self.btn_refresh_tree = QPushButton('Refresh')
        self.btn_refresh_tree.setProperty('ev_role', 'ghost')
        self.btn_refresh_tree.setEnabled(False)
        self.btn_refresh_tree.clicked.connect(self._refresh_tree)
        head.addWidget(self.btn_refresh_tree)
        layout.addLayout(head)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.btn_new_group = QPushButton('+ Group')
        self.btn_new_group.setEnabled(False)
        self.btn_new_group.clicked.connect(self._on_new_group)
        btn_row.addWidget(self.btn_new_group)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(20)
        self.tree.setRootIsDecorated(True)
        self.tree.setFocusPolicy(Qt.NoFocus)
        self.tree.setSelectionMode(QTreeWidget.SingleSelection)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        self.tree.itemClicked.connect(self._on_tree_item_clicked)
        layout.addWidget(self.tree, 1)

        self.current_project_label = QLabel('Current: -')
        self.current_project_label.setProperty('ev_role', 'section-caption')
        layout.addWidget(self.current_project_label)

        return frame

    # -- Right: image panel --

    def _build_image_panel(self) -> QWidget:
        self.image_panel = ImageTable(title='IMAGES')
        self.image_panel.log.connect(self._log)

        self.btn_import = QPushButton('Import Files')
        self.btn_import.setProperty('ev_role', 'primary')
        self.btn_import.setEnabled(False)
        self.btn_import.clicked.connect(self._on_import_files)
        self.btn_import_async = QPushButton('Import Async')
        self.btn_import_async.setEnabled(False)
        self.btn_import_async.clicked.connect(self._on_import_files_async)
        self.btn_delete_images = QPushButton('Delete Selected')
        self.btn_delete_images.setProperty('ev_role', 'danger')
        self.btn_delete_images.setEnabled(False)
        self.btn_delete_images.clicked.connect(self._on_delete_images)
        self.btn_image_info = QPushButton('Image Info')
        self.btn_image_info.setProperty('ev_role', 'ghost')
        self.btn_image_info.setEnabled(False)
        self.btn_image_info.clicked.connect(self._on_image_info)
        self.btn_cloud_status = QPushButton('Cloud Status')
        self.btn_cloud_status.setProperty('ev_role', 'ghost')
        self.btn_cloud_status.setEnabled(False)
        self.btn_cloud_status.clicked.connect(self._on_cloud_status)
        for btn in (self.btn_import, self.btn_import_async,
                    self.btn_delete_images, self.btn_image_info,
                    self.btn_cloud_status):
            self.image_panel.add_toolbar_widget(btn)
        self.image_panel.add_toolbar_stretch()

        return self.image_panel

    # -- Bottom: log panel --

    def _build_log_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName('panelCard')
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setMaximumHeight(200)
        inner = QVBoxLayout(frame)
        inner.setContentsMargins(12, 10, 12, 12)
        inner.setSpacing(8)

        head = QHBoxLayout()
        log_title = QLabel('EVENTS LOG')
        log_title.setProperty('ev_role', 'section-title')
        head.addWidget(log_title)
        head.addStretch()
        btn_clear = QPushButton('Clear')
        btn_clear.setProperty('ev_role', 'ghost')
        head.addWidget(btn_clear)
        inner.addLayout(head)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(
            'font-family: Menlo, Monaco, Consolas, monospace; font-size: 12px; '
            'background-color: #0a0a0a; color: #d8d8d8; '
            'border: 1px solid rgba(255, 255, 255, 0.05); '
            'border-radius: 6px; padding: 6px;')
        btn_clear.clicked.connect(self.log_view.clear)
        inner.addWidget(self.log_view, 1)

        return frame

    # ----------------------------------------------------------- Helpers --

    def _log(self, msg: str):
        self.log_received.emit(msg)

    def _append_log(self, msg: str):
        self.log_view.append(msg)
        logger.info(msg)

    def _set_tree_buttons_enabled(self, enabled: bool):
        self.btn_refresh_tree.setEnabled(enabled)
        self.btn_new_group.setEnabled(enabled)

    def _set_image_buttons_enabled(self, enabled: bool):
        self.image_panel.set_enabled(enabled)
        self.btn_import.setEnabled(enabled)
        self.btn_import_async.setEnabled(enabled)
        self.btn_delete_images.setEnabled(enabled)
        self.btn_image_info.setEnabled(enabled)
        self.btn_cloud_status.setEnabled(enabled)

    @staticmethod
    def _coerce_id(value) -> int | None:
        """Return ``value`` as ``int`` or ``None`` if it cannot be coerced."""
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _is_stale_resource_error(exc: BaseException) -> bool:
        """True if the host says the target group/project no longer exists.

        Covers the common "ghost UI" case: user deleted a group/project
        elsewhere (or double-clicked our own delete) and this demo's tree
        still holds the old id. ``ApiError.code`` is exposed as a plain
        attribute by the SDK so we duck-type it here without importing
        internal exception classes.
        """
        code = getattr(exc, 'code', None)
        return code in (404, 410)

    def _recover_from_stale(self, context: str) -> None:
        """Silently refresh the tree after a stale-resource error.

        We skip the popup because the situation is benign -
        the host state just moved faster than the UI - and showing a
        noisy error dialog every time would train the user to dismiss
        it. Log line is still emitted so the flow is debuggable.
        """
        self._log(f'{context}: resource gone on host; refreshing tree')
        self._refresh_tree()

    def _clear_current_project(self) -> None:
        """Drop the current project selection and disable image actions."""
        self._current_project_id = None
        self._current_project_name = ''
        self.current_project_label.setText('Current: -')
        self.image_panel.clear()
        self._set_image_buttons_enabled(False)

    @staticmethod
    def _group_item_label(item: QTreeWidgetItem) -> str:
        """Extract group display name from the custom widget or fallback to text."""
        w = item.treeWidget().itemWidget(item, 0)
        if w:
            lbl = w.findChild(QLabel)
            if lbl:
                return lbl.text().split('  (')[0]
        return item.text(0).split('  (')[0]

    # ------------------------------------------------------- Connection --

    def _on_connected(self):
        self._log('Connected')
        self._set_tree_buttons_enabled(True)

        try:
            evoto.image.subscribe(import_listener_uuid=MY_IMPORT_LISTENER_UUID)
            self._log(f'Subscribed to import events (uuid={MY_IMPORT_LISTENER_UUID})')
        except Exception as exc:
            self._log(f'Failed to subscribe import events: {exc}')

        self._refresh_tree()
        self._load_current_project()

    def _on_disconnected(self):
        self._log('Disconnected')
        self._set_tree_buttons_enabled(False)
        self._set_image_buttons_enabled(False)
        self._current_project_id = None
        self._current_project_name = ''
        self.current_project_label.setText('Current: -')

    def _on_connect_failed(self, reason: str):
        # Surface the real host-side rejection reason (e.g. 409 Conflict /
        # 403 Forbidden) in the UI log so users see more than just "Failed".
        self._log(f'Connect failed: {reason}')

    # --------------------------------------------------- Project Tree ---

    def _refresh_tree(self):
        self._log('Loading groups and projects...')
        self.tree.clear()
        # Collect live project ids so we can tell whether the
        # currently-selected project still exists after the refresh.
        live_project_ids: set[int] = set()
        try:
            groups = evoto.project.group_list()
            self._log(f'Loaded {len(groups)} group(s)')

            for g in groups:
                gid = g.get('id')
                gname = g.get('name', 'Unnamed Group')
                group_item = QTreeWidgetItem(self.tree)
                group_item.setData(0, ROLE_ID, gid)
                group_item.setData(0, ROLE_TYPE, NODE_GROUP)
                group_item.setFlags(group_item.flags() & ~Qt.ItemIsSelectable)

                try:
                    projects = evoto.project.list(group_id=gid)
                    for p in projects:
                        pid = p.get('id')
                        pname = p.get('name', 'Unnamed Project')
                        is_cloud = bool(p.get('is_cloud'))
                        proj_item = QTreeWidgetItem(group_item)
                        cloud_suffix = '  [Cloud]' if is_cloud else ''
                        proj_item.setText(0, f'{pname}{cloud_suffix}  (ID: {pid})')
                        proj_item.setData(0, ROLE_ID, pid)
                        proj_item.setData(0, ROLE_TYPE, NODE_PROJECT)
                        proj_item.setData(0, ROLE_IS_CLOUD, is_cloud)
                        pid_int = self._coerce_id(pid)
                        if pid_int is not None:
                            live_project_ids.add(pid_int)
                    display_name = f'{gname}  ({len(projects)})'
                except Exception as exc:
                    self._log(f'Failed to load projects for group {gid}: {exc}')
                    display_name = gname

                row_widget = QWidget()
                row_widget.setStyleSheet('background: transparent;')
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(6)
                lbl = QLabel(display_name)
                lbl.setStyleSheet('color: #f3f0e8; background: transparent;')
                row_layout.addWidget(lbl, 1)
                add_btn = QPushButton('+')
                add_btn.setFixedSize(16, 16)
                add_btn.setCursor(Qt.PointingHandCursor)
                add_btn.setStyleSheet(
                    'QPushButton { background: transparent; color: #666; '
                    'border: 1px solid #555; border-radius: 2px; font-size: 10px; '
                    'padding: 2px; margin: 0; '
                    'min-height: 0px; max-height: 16px; '
                    'min-width: 0px; max-width: 16px; }'
                    'QPushButton:hover { color: #fff; border-color: #888; }'
                    'QToolTip { background: #333; color: #eee; border: 1px solid #555; '
                    'padding: 3px 6px; }'
                )
                add_btn.setToolTip(f'New project in "{gname}"')
                add_btn.clicked.connect(lambda _, g_id=gid: self._ctx_new_project(g_id))
                row_layout.addWidget(add_btn, 0)
                self.tree.setItemWidget(group_item, 0, row_widget)

                group_item.setExpanded(True)

        except Exception as exc:
            self._log(f'Failed to load groups: {exc}')

        # Self-heal: if the tree no longer contains the currently-selected
        # project (it was deleted elsewhere, or its group was), clear the
        # selection so the image panel does not keep calling into a
        # non-existent project.
        if self._current_project_id is not None and \
                self._current_project_id not in live_project_ids:
            self._log(
                f'Current project {self._current_project_id} no longer exists; '
                'clearing selection'
            )
            self._clear_current_project()

        self._highlight_current_project()

    def _load_current_project(self):
        try:
            result = evoto.project.current()
            proj = result.get('project', {})
            pid = proj.get('id')
            name = proj.get('name', '')
            if pid:
                self._current_project_id = int(pid)
                self._current_project_name = name
                self.current_project_label.setText(f'Current: {name} (ID: {pid})')
                self._log(f'Current project: {name} (ID: {pid})')
                self._highlight_current_project()
                self._select_project(self._current_project_id)
        except Exception as exc:
            self._log(f'No current project: {exc}')

    def _highlight_current_project(self):
        if not self._current_project_id:
            return
        for gi in range(self.tree.topLevelItemCount()):
            group_item = self.tree.topLevelItem(gi)
            for pi in range(group_item.childCount()):
                proj_item = group_item.child(pi)
                pid = proj_item.data(0, ROLE_ID)
                if pid == self._current_project_id:
                    self.tree.setCurrentItem(proj_item)
                    return

    def _select_project(self, project_id: int, project_name: str = ''):
        self._current_project_id = project_id
        if project_name:
            self._current_project_name = project_name
        self._set_image_buttons_enabled(True)
        self._refresh_images()

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, _col: int):
        node_type = item.data(0, ROLE_TYPE)
        if node_type == NODE_GROUP:
            item.setExpanded(not item.isExpanded())
            return
        if node_type == NODE_PROJECT:
            pid = item.data(0, ROLE_ID)
            if pid is not None:
                label = item.text(0).split('  (ID:')[0]
                self._select_project(int(pid), label)

    # ------------------------------------------------- Context Menu ---

    def _on_tree_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if item is None:
            return
        if not self.connect_bar.is_connected():
            return

        menu = QMenu(self)
        menu.setStyleSheet(MENU_QSS)
        node_type = item.data(0, ROLE_TYPE)
        node_id = item.data(0, ROLE_ID)

        if node_type == NODE_GROUP:
            menu.addAction('New Project Here', lambda: self._ctx_new_project(node_id))
            menu.addSeparator()
            menu.addAction('Rename Group', lambda: self._ctx_rename_group(item, node_id))
            menu.addAction('Delete Group', lambda: self._ctx_delete_group(node_id))
        elif node_type == NODE_PROJECT:
            menu.addAction('Switch in Host', lambda: self._ctx_switch_project(item, node_id))
            convert_action = menu.addAction(
                'Convert to Cloud',
                lambda: self._ctx_convert_project_to_cloud(item, node_id),
            )
            convert_action.setEnabled(not bool(item.data(0, ROLE_IS_CLOUD)))
            stop_loading_action = menu.addAction(
                'Stop Cloud Loading',
                lambda: self._ctx_stop_cloud_loading(node_id),
            )
            stop_loading_action.setEnabled(bool(item.data(0, ROLE_IS_CLOUD)))
            menu.addAction('Cloud Status', lambda: self._ctx_cloud_status(node_id))
            menu.addSeparator()
            menu.addAction('Rename', lambda: self._ctx_rename_project(item, node_id))
            menu.addAction('Get Info', lambda: self._ctx_get_project_info(node_id))
            menu.addSeparator()
            menu.addAction('Delete', lambda: self._ctx_delete_project(node_id))

        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _ctx_new_project(self, group_id):
        name, ok = QInputDialog.getText(self, 'New Project', 'Project name:')
        if not ok or not name.strip():
            return
        try:
            result = evoto.project.create(name.strip(), group_id=group_id)
            pid = result.get('project', {}).get('id', result.get('id', ''))
            self._log(f'Created project "{name.strip()}" (ID: {pid}) in group {group_id}')
            self._refresh_tree()
        except Exception as exc:
            self._log(f'Failed to create project: {exc}')
            # Creating into a ghost group - silently refresh so the
            # stale group disappears from the tree.
            if self._is_stale_resource_error(exc):
                self._recover_from_stale('Create project')
                return
            themed_message(self, 'Error', str(exc))

    def _ctx_rename_group(self, item: QTreeWidgetItem, group_id):
        current_name = self._group_item_label(item)
        name, ok = QInputDialog.getText(self, 'Rename Group', 'New name:', text=current_name)
        if not ok or not name.strip():
            return
        try:
            evoto.project.group_rename(group_id, name.strip())
            self._log(f'Renamed group {group_id} to "{name.strip()}"')
            self._refresh_tree()
        except Exception as exc:
            self._log(f'Failed to rename group: {exc}')
            if self._is_stale_resource_error(exc):
                self._recover_from_stale('Rename group')
                return
            themed_message(self, 'Error', str(exc))

    def _ctx_delete_group(self, group_id):
        if not themed_confirm(
            self, 'Delete Group',
            f'Delete group {group_id} and all its projects?',
            informative='The group and every project inside it will be '
                        'moved to the Evoto Recycle Bin; you can restore '
                        'them from there.',
            yes_text='Delete', danger=True,
        ):
            return
        try:
            result = evoto.project.group_delete(group_id)
            self._log(f'Deleted group group_ids={[group_id]} result={result}')
            # _refresh_tree() below will notice if the current project
            # lived inside the deleted group and clear the selection.
            self._refresh_tree()
        except Exception as exc:
            self._log(f'Failed to delete group: {exc}')
            if self._is_stale_resource_error(exc):
                self._recover_from_stale('Delete group')
                return
            themed_message(self, 'Error', str(exc))

    def _ctx_rename_project(self, item: QTreeWidgetItem, project_id):
        current_name = item.text(0).split('  (ID:')[0]
        name, ok = QInputDialog.getText(self, 'Rename Project', 'New name:', text=current_name)
        if not ok or not name.strip():
            return
        try:
            evoto.project.rename(project_id, name.strip())
            self._log(f'Renamed project {project_id} to "{name.strip()}"')
            self._refresh_tree()
        except Exception as exc:
            self._log(f'Failed to rename project: {exc}')
            if self._is_stale_resource_error(exc):
                self._recover_from_stale('Rename project')
                return
            themed_message(self, 'Error', str(exc))

    def _ctx_get_project_info(self, project_id):
        try:
            result = evoto.project.info(project_id)
            self._log(f'Project info:\n{pformat(result)}')
        except Exception as exc:
            self._log(f'Failed to get project info: {exc}')
            if self._is_stale_resource_error(exc):
                self._recover_from_stale('Get project info')

    def _ctx_switch_project(self, item: QTreeWidgetItem, project_id):
        try:
            result = evoto.project.switch(project_id)
            self._log(f'Project switch accepted:\n{pformat(result)}')
        except Exception as exc:
            self._log(f'Failed to switch project: {exc}')
            if self._is_stale_resource_error(exc):
                self._recover_from_stale('Switch project')
                return
            themed_message(self, 'Error', str(exc))

    def _ctx_convert_project_to_cloud(self, item: QTreeWidgetItem, project_id):
        project_id_int = self._coerce_id(project_id)
        if project_id_int is None:
            return
        project_name = item.text(0).split('  [Cloud]')[0].split('  (ID:')[0]
        if not themed_confirm(
            self, 'Convert to Cloud',
            f'Convert "{project_name}" to a cloud project?',
            informative='The host will accept the request immediately. Final '
                        'success or failure is reported by project.convertToCloud events.',
            yes_text='Convert',
        ):
            return
        try:
            result = evoto.project.convert_to_cloud(project_id_int)
            self._log(f'Convert to cloud accepted:\n{pformat(result)}')
        except Exception as exc:
            self._log(f'Failed to convert project to cloud: {exc}')
            if self._is_stale_resource_error(exc):
                self._recover_from_stale('Convert project to cloud')
                return
            themed_message(self, 'Error', str(exc))

    def _ctx_stop_cloud_loading(self, project_id):
        project_id_int = self._coerce_id(project_id)
        if project_id_int is None:
            return
        try:
            result = evoto.project.stop_cloud_loading(project_id_int)
            self._log(f'Stop cloud loading:\n{pformat(result)}')
        except Exception as exc:
            self._log(f'Failed to stop cloud loading: {exc}')
            if self._is_stale_resource_error(exc):
                self._recover_from_stale('Stop cloud loading')
                return
            themed_message(self, 'Error', str(exc))

    def _ctx_cloud_status(self, project_id):
        project_id_int = self._coerce_id(project_id)
        if project_id_int is None:
            return
        try:
            result = evoto.project.cloud_status(project_id_int)
            self._log(f'Cloud status:\n{pformat(result)}')
        except Exception as exc:
            self._log(f'Failed to query cloud status: {exc}')
            if self._is_stale_resource_error(exc):
                self._recover_from_stale('Cloud status')
                return
            themed_message(self, 'Error', str(exc))

    def _ctx_delete_project(self, project_id):
        if not themed_confirm(
            self, 'Delete Project',
            f'Delete project {project_id}?',
            informative='The project will be moved to the Evoto Recycle '
                        'Bin. You can restore it from there later.',
            yes_text='Delete', danger=True,
        ):
            return
        try:
            evoto.project.delete(project_id)
            self._log(f'Deleted project {project_id}')
            if self._current_project_id == project_id:
                self._clear_current_project()
            self._refresh_tree()
        except Exception as exc:
            self._log(f'Failed to delete project: {exc}')
            if self._is_stale_resource_error(exc):
                # The project vanished before we could delete it;
                # proceed as if the delete succeeded.
                if self._current_project_id == project_id:
                    self._clear_current_project()
                self._recover_from_stale('Delete project')
                return
            themed_message(self, 'Error', str(exc))

    # --------------------------------------------- New Group / Project ---

    def _on_new_group(self):
        name, ok = QInputDialog.getText(self, 'New Group', 'Group name:')
        if not ok or not name.strip():
            return
        try:
            result = evoto.project.group_create(name.strip())
            gid = result.get('group', {}).get('id', result.get('id', ''))
            self._log(f'Created group "{name.strip()}" (ID: {gid})')
            self._refresh_tree()
        except Exception as exc:
            self._log(f'Failed to create group: {exc}')
            # group_create doesn't take a stale id, so a 404 here is very
            # unlikely - but keep the symmetry so we never pop a
            # confusing error dialog when the host state drifted.
            if self._is_stale_resource_error(exc):
                self._recover_from_stale('Create group')
                return
            themed_message(self, 'Error', str(exc))

    # --------------------------------------------------- Image Panel ---

    def _refresh_images(self):
        if not self._current_project_id:
            self.image_panel.clear()
            return
        name = self._current_project_name or ''
        self._log(f'Loading images for project {self._current_project_id}...')
        self.image_panel.set_project(self._current_project_id, name)

    def _on_import_files(self):
        if not self._current_project_id:
            themed_message(self, 'Error', 'Select a project first')
            return
        paths, _ = QFileDialog.getOpenFileNames(self, 'Select files to import')
        if not paths:
            return
        self._log(f'Importing {len(paths)} file(s) synchronously...')
        try:
            result = evoto.image.import_files(
                paths,
                project_id=self._current_project_id,
                import_listener_uuid=MY_IMPORT_LISTENER_UUID,
            )
            self._log(f'Import result:\n{pformat(result)}')
            self._refresh_images()
        except Exception as exc:
            self._log(f'Import failed: {exc}')
            # Target project was deleted between selection and import.
            if self._is_stale_resource_error(exc):
                self._recover_from_stale('Import files')
                return
            themed_message(self, 'Import Failed', str(exc))

    def _on_import_files_async(self):
        if not self._current_project_id:
            themed_message(self, 'Error', 'Select a project first')
            return
        paths, _ = QFileDialog.getOpenFileNames(self, 'Select files to import')
        if not paths:
            return
        self._log(f'Importing {len(paths)} file(s) asynchronously...')
        try:
            result = evoto.image.import_files_async(
                paths,
                project_id=self._current_project_id,
                import_listener_uuid=MY_IMPORT_LISTENER_UUID,
            )
            import_id = result.get('import_id', '')
            self._log(f'Async import started: import_id={import_id}\n{pformat(result)}')
        except Exception as exc:
            self._log(f'Async import failed: {exc}')
            if self._is_stale_resource_error(exc):
                self._recover_from_stale('Import files (async)')
                return
            themed_message(self, 'Import Failed', str(exc))

    def _on_cloud_status(self):
        if not self._current_project_id:
            themed_message(self, 'Error', 'Select a project first')
            return
        self._ctx_cloud_status(self._current_project_id)

    def _selected_image_ids(self) -> list[int]:
        return self.image_panel.selected_image_ids()

    def _on_delete_images(self):
        if not self._current_project_id:
            return
        image_ids = self._selected_image_ids()
        if not image_ids:
            themed_message(self, 'Hint', 'Select images to delete')
            return
        if not themed_confirm(
            self, 'Delete Images',
            f'Delete {len(image_ids)} image(s)?',
            informative='The selected images will be moved to the Evoto '
                        'Recycle Bin. You can restore them from there '
                        'later.',
            yes_text='Delete', danger=True,
        ):
            return
        self._log(f'Deleting {len(image_ids)} image(s): {image_ids}')
        try:
            result = evoto.image.delete(imageIds=image_ids)
            self._log(f'Delete task accepted:\n{pformat(result)}')
            QTimer.singleShot(1000, self._refresh_images)
        except Exception as exc:
            self._log(f'Delete failed: {exc}')
            if self._is_stale_resource_error(exc):
                # Images (or their project) are gone; refresh both
                # tree and image panel to shake the stale rows out.
                self._recover_from_stale('Delete images')
                self._refresh_images()
                return
            themed_message(self, 'Error', str(exc))

    @staticmethod
    def _format_metadata(metadata: dict) -> str:
        """Pretty-print ``ImageInfo.metadata`` - a nested
        ``{TableName: {field: value}}`` structure.

        Returns ``    (empty)`` when ``metadata`` is empty. Otherwise each
        table is indented 4 spaces with its fields indented 6 spaces;
        tables and fields are sorted alphabetically so the output is
        stable and diff-friendly across runs.
        """
        if not metadata:
            return '    (empty)'
        lines: list[str] = []
        for table_name in sorted(metadata):
            fields = metadata.get(table_name) or {}
            lines.append(f'    {table_name}:')
            if not isinstance(fields, dict) or not fields:
                lines.append('      (empty)')
                continue
            for field_name in sorted(fields):
                lines.append(f'      {field_name} = {fields[field_name]}')
        return '\n'.join(lines)

    def _on_image_info(self):
        image_ids = self._selected_image_ids()
        if not image_ids:
            themed_message(self, 'Error', 'Select one or more image rows first')
            return

        self._log(f'Fetching info for {len(image_ids)} image(s): {image_ids}')
        succeeded: list[str] = []
        failed: list[tuple[int, str]] = []
        for image_id in image_ids:
            try:
                info = evoto.image.info(image_id)
                metadata_block = self._format_metadata(info.metadata)
                succeeded.append(
                    f'[id={info.id}] {info.filename}\n'
                    f'  origin_path = {info.origin_path}\n'
                    f'  project_id  = {info.project_id}\n'
                    f'  format      = {info.format}\n'
                    f'  size        = {info.width} x {info.height}\n'
                    f'  file_size   = {info.file_size} bytes\n'
                    f'  metadata    :\n{metadata_block}'
                )
            except Exception as exc:
                failed.append((image_id, str(exc)))

        if succeeded:
            sep = '\n' + '-' * 60 + '\n'
            self._log(
                f'Image info ({len(succeeded)}/{len(image_ids)} ok):\n'
                + sep.join(succeeded)
            )
        if failed:
            self._log(
                f'Image info failed for {len(failed)} image(s):\n'
                + '\n'.join(f'  id={iid}: {err}' for iid, err in failed)
            )

    # ------------------------------------------------- Import Events ---

    def _on_import_event(self, event_name: str, data: object):
        payload = data if isinstance(data, dict) else {}
        import_id = payload.get('import_id', '')
        progress = payload.get('progress', '')
        self._log(f'{event_name}: import_id={import_id} progress={progress}')

        if event_name in ('import.completed', 'import.failed'):
            self._log(f'{event_name} detail:\n{pformat(payload)}')
            self._refresh_images()

    # --------------------------------------------------------- Close ---

    def closeEvent(self, event):
        evoto.shutdown()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = ProjectImageDemoWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
