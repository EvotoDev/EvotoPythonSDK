"""Preset Export Demo - export images with custom settings or export presets.

Demonstrates:
- ``ExportAPI.start_with_custom()`` - custom export with preset suits + options
- ``ExportAPI.start_with_export_preset()`` - export using saved export presets
- ``ExportAPI.list_export_presets()`` - list saved export configurations
- Full lifecycle event tracking (started/progress/item_finished/completed/failed)
"""

import logging
import sys
from pathlib import Path
from pprint import pformat

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import evoto
from evoto.core.api_commands import ExportCmd
from evoto.core.api_fields import ExportField, Field

from demo.shared import (
    apply_theme, themed_message,
    ConnectBar, ProjectImageLoader, PresetTreeWidget, ImageTable,
    ExportOptionsPanel,
)

try:
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtWidgets import (
        QApplication, QButtonGroup, QCheckBox, QFileDialog,
        QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
        QListWidgetItem, QPushButton, QSizePolicy,
        QSplitter, QStackedWidget, QTableWidget,
        QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
    )
    PYQT_IMPORT_ERROR = None
except ModuleNotFoundError as exc:
    PYQT_IMPORT_ERROR = exc

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger('preset_export_demo')

MY_LISTENER_UUID = "preset-export-demo-a1b2c3d4"


if PYQT_IMPORT_ERROR is None:

    class PresetExportDemoWindow(QWidget):
        event_received = Signal(str, object)
        log_received = Signal(str)

        def __init__(self):
            super().__init__()
            self._image_ids: list[int] = []

            self.event_received.connect(self._on_event_main)
            self.log_received.connect(self._append_log)
            self._register_event_handlers()
            self._init_ui()
            apply_theme(self)

        def _register_event_handlers(self):
            for evt in ('export.started', 'export.progress', 'export.item_finished',
                        'export.completed', 'export.failed'):
                evoto.on(evt, lambda data, e=evt: self.event_received.emit(e, data))

        # ---- UI ----

        def _init_ui(self):
            self.setWindowTitle('Preset Export Demo')
            self.resize(1200, 780)

            root = QVBoxLayout(self)
            root.setContentsMargins(16, 16, 16, 16)
            root.setSpacing(12)

            # --- Banner ---
            self.connect_bar = ConnectBar(title='Preset Export')
            self.connect_bar.connected.connect(self._on_connected)
            self.connect_bar.disconnected.connect(self._on_disconnected)
            self.connect_bar.connection_failed.connect(self._on_connect_failed)
            root.addWidget(self.connect_bar)

            # --- Main content ---
            flow = QHBoxLayout()
            flow.setSpacing(12)

            # -- Left column --
            left_col = QWidget()
            left_col_layout = QVBoxLayout(left_col)
            left_col_layout.setContentsMargins(0, 0, 0, 0)
            left_col_layout.setSpacing(6)

            # Workflow request (project + images)
            self.loader = ProjectImageLoader(title='WORKFLOW REQUEST')
            self.loader.log.connect(self._log)
            self.loader.project_loaded.connect(self._on_project_loaded)
            self.loader.images_loaded.connect(self._on_images_loaded)

            self.chk_use_uuid = QCheckBox(f'Export Listener ID: {MY_LISTENER_UUID}')
            self.chk_use_uuid.setChecked(True)
            self.chk_use_uuid.stateChanged.connect(self._on_uuid_toggled)
            self.loader.layout().insertWidget(0, self.chk_use_uuid)

            left_col_layout.addWidget(self.loader, 0)

            # Mode tabs
            tab_row = QHBoxLayout()
            tab_row.setSpacing(8)
            self._mode_tab_group = QButtonGroup(self)
            self.btn_tab_custom = QPushButton('Custom')
            self.btn_tab_preset = QPushButton('Export Presets')
            for b in (self.btn_tab_custom, self.btn_tab_preset):
                b.setCheckable(True)
                b.setMinimumHeight(24)
                b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self._mode_tab_group.addButton(self.btn_tab_custom, 0)
            self._mode_tab_group.addButton(self.btn_tab_preset, 1)
            self.btn_tab_custom.setChecked(True)
            self._mode_tab_group.buttonClicked.connect(lambda _: self._sync_export_mode_ui())
            tab_row.addWidget(self.btn_tab_custom, 1)
            tab_row.addWidget(self.btn_tab_preset, 1)
            left_col_layout.addLayout(tab_row)

            # --- Custom mode: preset tree + export options ---
            self.mode_options_stack = QStackedWidget()

            custom_page = QWidget()
            custom_page_layout = QVBoxLayout(custom_page)
            custom_page_layout.setContentsMargins(0, 2, 0, 0)
            custom_page_layout.setSpacing(4)
            self._build_custom_export_options(custom_page_layout)

            preset_page = QWidget()
            QVBoxLayout(preset_page).setContentsMargins(0, 0, 0, 0)

            self.mode_options_stack.addWidget(custom_page)
            self.mode_options_stack.addWidget(preset_page)

            # Preset list stacks
            self.flow_right_stack = QStackedWidget()

            # Custom mode: shared PresetTreeWidget (multi-select)
            self.preset_tree = PresetTreeWidget(multi_select=True)
            self.preset_tree.log.connect(self._log)
            self.flow_right_stack.addWidget(self.preset_tree)

            # Export Preset mode: export preset list
            self.export_preset_group = QFrame()
            self.export_preset_group.setFrameShape(QFrame.StyledPanel)
            self.export_preset_group.setObjectName('optionCard')
            ep_layout = QVBoxLayout(self.export_preset_group)
            ep_layout.setContentsMargins(8, 8, 8, 8)
            ep_layout.setSpacing(4)
            ep_head = QHBoxLayout()
            ep_title = QLabel('EXPORT PRESETS')
            ep_title.setProperty('ev_role', 'section-title')
            ep_head.addWidget(ep_title)
            ep_head.addStretch()
            self.btn_refresh_export_presets = QPushButton('Refresh')
            self.btn_refresh_export_presets.setProperty('ev_role', 'ghost')
            self.btn_refresh_export_presets.setEnabled(False)
            self.btn_refresh_export_presets.clicked.connect(self._on_refresh_export_presets)
            ep_head.addWidget(self.btn_refresh_export_presets)
            ep_layout.addLayout(ep_head)
            self.export_preset_list = QListWidget()
            self.export_preset_list.setSelectionMode(QListWidget.MultiSelection)
            ep_layout.addWidget(self.export_preset_list)
            self.flow_right_stack.addWidget(self.export_preset_group)

            left_col_layout.addWidget(self.flow_right_stack, 1)
            left_col_layout.addWidget(self.mode_options_stack, 0)

            # Export button
            self.btn_export = QPushButton('Start Export')
            self.btn_export.setProperty('ev_role', 'primary')
            self.btn_export.setMinimumHeight(28)
            self.btn_export.setEnabled(False)
            self.btn_export.clicked.connect(self._on_start_export)
            left_col_layout.addWidget(self.btn_export)

            flow.addWidget(left_col, 1)

            # -- Right column: Image Picker + Task Queue + Log (vertically resizable) --
            right_splitter = QSplitter(Qt.Vertical)
            self.image_table = ImageTable(
                title='IMAGES',
                hint='Pick rows to include in the export. Falls back to all loaded IDs if none selected.',
            )
            self.image_table.log.connect(self._log)
            right_splitter.addWidget(self.image_table)

            task_host = QWidget()
            task_host_layout = QVBoxLayout(task_host)
            task_host_layout.setContentsMargins(0, 0, 0, 0)
            task_host_layout.setSpacing(0)
            self._build_task_queue(task_host_layout)
            right_splitter.addWidget(task_host)

            log_host = QWidget()
            log_host_layout = QVBoxLayout(log_host)
            log_host_layout.setContentsMargins(0, 0, 0, 0)
            log_host_layout.setSpacing(0)
            self._build_log_panel(log_host_layout)
            right_splitter.addWidget(log_host)

            right_splitter.setStretchFactor(0, 3)
            right_splitter.setStretchFactor(1, 2)
            right_splitter.setStretchFactor(2, 1)
            right_splitter.setSizes([360, 240, 140])

            flow.addWidget(right_splitter, 1)
            root.addLayout(flow, 1)

            self._sync_export_mode_ui()

        def _build_custom_export_options(self, layout):
            """Build the Format + Quality + Output Dir cards.

            Format and Quality are rendered by the shared
            :class:`ExportOptionsPanel`; this method only adds the
            demo-specific Export Dir row on top.
            """

            self.options_panel = ExportOptionsPanel()
            layout.addWidget(self.options_panel)

            c_dir = QFrame()
            c_dir.setFrameShape(QFrame.StyledPanel)
            c_dir.setObjectName('optionCard')
            dir_card_layout = QHBoxLayout(c_dir)
            dir_card_layout.setContentsMargins(8, 6, 8, 6)
            dir_card_layout.setSpacing(4)
            dir_label = QLabel('Export Dir')
            dir_label.setProperty('ev_role', 'field-label')
            dir_label.setFixedWidth(70)
            dir_card_layout.addWidget(dir_label)
            self.export_dir_input = QLineEdit()
            self.export_dir_input.setPlaceholderText('Output directory')
            dir_card_layout.addWidget(self.export_dir_input, 1)
            btn_browse = QPushButton('Browse')
            btn_browse.clicked.connect(self._browse_dir)
            dir_card_layout.addWidget(btn_browse)
            layout.addWidget(c_dir)

        def _build_task_queue(self, parent_layout):
            task_frame = QFrame()
            task_frame.setFrameShape(QFrame.StyledPanel)
            task_frame.setObjectName('optionCard')
            task_inner = QVBoxLayout(task_frame)
            task_inner.setContentsMargins(8, 8, 8, 8)
            task_inner.setSpacing(4)

            task_head = QHBoxLayout()
            tb_title = QLabel('TASK QUEUE')
            tb_title.setProperty('ev_role', 'section-title')
            task_head.addWidget(tb_title)
            task_head.addStretch()
            self.btn_query_all = QPushButton('Refresh')
            self.btn_query_all.setProperty('ev_role', 'ghost')
            self.btn_query_all.setEnabled(False)
            self.btn_query_all.clicked.connect(self._on_query_all)
            task_head.addWidget(self.btn_query_all)
            self.btn_task_exporting = QPushButton('Exporting')
            self.btn_task_exporting.setObjectName('taskSegBtn')
            self.btn_task_exporting.setCheckable(True)
            self.btn_task_completed = QPushButton('Completed')
            self.btn_task_completed.setObjectName('taskSegBtn')
            self.btn_task_completed.setCheckable(True)
            self._task_view_group = QButtonGroup(self)
            self._task_view_group.setExclusive(True)
            self._task_view_group.addButton(self.btn_task_exporting, 0)
            self._task_view_group.addButton(self.btn_task_completed, 1)
            self.btn_task_exporting.setChecked(True)
            self._task_view_group.buttonClicked.connect(
                lambda btn: self.task_view_stack.setCurrentIndex(0 if btn is self.btn_task_exporting else 1))
            task_head.addWidget(self.btn_task_exporting)
            task_head.addWidget(self.btn_task_completed)
            task_inner.addLayout(task_head)

            def _make_table():
                t = QTableWidget(0, 5)
                t.setHorizontalHeaderLabels(['Dir ID', 'Name', 'Count', 'Path', 'Actions'])
                h = t.horizontalHeader()
                h.setStretchLastSection(False)
                h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
                h.setSectionResizeMode(1, QHeaderView.Stretch)
                h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
                h.setSectionResizeMode(3, QHeaderView.Stretch)
                h.setSectionResizeMode(4, QHeaderView.Fixed)
                h.resizeSection(4, 160)
                t.setEditTriggers(QTableWidget.NoEditTriggers)
                t.setSelectionBehavior(QTableWidget.SelectRows)
                t.verticalHeader().setVisible(False)
                t.verticalHeader().setDefaultSectionSize(46)
                return t

            self.exporting_table = _make_table()
            self.completed_table = _make_table()
            self.task_view_stack = QStackedWidget()
            self.task_view_stack.addWidget(self.exporting_table)
            self.task_view_stack.addWidget(self.completed_table)
            task_inner.addWidget(self.task_view_stack)
            parent_layout.addWidget(task_frame, 1)

        def _build_log_panel(self, parent_layout):
            log_frame = QFrame()
            log_frame.setFrameShape(QFrame.StyledPanel)
            log_frame.setObjectName('optionCard')
            log_inner = QVBoxLayout(log_frame)
            log_inner.setContentsMargins(8, 8, 8, 8)
            log_inner.setSpacing(4)
            log_head = QHBoxLayout()
            log_title = QLabel('EVENTS LOG')
            log_title.setProperty('ev_role', 'section-title')
            log_head.addWidget(log_title)
            log_head.addStretch()
            btn_clear = QPushButton('Clear')
            btn_clear.setProperty('ev_role', 'ghost')
            log_head.addWidget(btn_clear)
            log_inner.addLayout(log_head)
            self.log_view = QTextEdit()
            self.log_view.setReadOnly(True)
            self.log_view.setStyleSheet(
                'font-family: Menlo, Monaco, Consolas, monospace; font-size: 12px;')
            btn_clear.clicked.connect(self.log_view.clear)
            log_inner.addWidget(self.log_view)
            parent_layout.addWidget(log_frame, 1)

        # ---- Helpers ----

        def _append_log(self, msg: str):
            self.log_view.append(msg)
            logger.info(msg)

        def _log(self, msg: str):
            self.log_received.emit(msg)

        def _browse_dir(self):
            path = QFileDialog.getExistingDirectory(self, 'Select export directory')
            if path:
                self.export_dir_input.setText(path)

        def _build_options(self) -> dict | None:
            result = self.options_panel.to_options()
            return result if result else None

        # ---- Connection ----

        def _on_connected(self):
            self._log('Connected')
            self.loader.set_enabled(True)
            self.preset_tree.set_enabled(True)
            self.image_table.set_enabled(True)
            self.btn_refresh_export_presets.setEnabled(True)
            self.btn_export.setEnabled(True)
            self.btn_query_all.setEnabled(True)

            try:
                sub_uuid = MY_LISTENER_UUID if self.chk_use_uuid.isChecked() else None
                evoto.export.subscribe(export_listener_uuid=sub_uuid)
                self._log(f'Subscribed to export events (uuid={sub_uuid or "ALL"})')
            except Exception as exc:
                self._log(f'Failed to subscribe: {exc}')

            self.loader.auto_load(max_images=0)
            self.preset_tree.refresh()
            self._on_refresh_export_presets()
            self._on_query_all()

        def _on_disconnected(self):
            self._log('Disconnected')
            self.loader.set_enabled(False)
            self.preset_tree.set_enabled(False)
            self.image_table.set_enabled(False)
            self.image_table.clear()
            self.btn_refresh_export_presets.setEnabled(False)
            self.btn_export.setEnabled(False)
            self.btn_query_all.setEnabled(False)

        def _on_connect_failed(self, reason: str):
            # Surface the real host-side rejection reason (e.g. 409 Conflict /
            # 403 Forbidden) in the UI log so users see more than just "Failed".
            self._log(f'Connect failed: {reason}')

        def _on_project_loaded(self, project_id: int, name: str):
            self.image_table.set_project(project_id, name)

        def _on_uuid_toggled(self):
            if not self.connect_bar.is_connected():
                return
            try:
                sub_uuid = MY_LISTENER_UUID if self.chk_use_uuid.isChecked() else None
                evoto.export.subscribe(export_listener_uuid=sub_uuid)
                self._log(f'Re-subscribed (uuid={sub_uuid or "ALL"})')
            except Exception as exc:
                self._log(f'Re-subscribe failed: {exc}')

        def _on_images_loaded(self, ids: list):
            self._image_ids = list(ids)

        # ---- Export mode ----

        def _current_export_mode(self) -> str:
            return 'custom' if self.btn_tab_custom.isChecked() else 'export_preset'

        def _sync_export_mode_ui(self):
            is_custom = self._current_export_mode() == 'custom'
            self.flow_right_stack.setCurrentIndex(0 if is_custom else 1)
            self.mode_options_stack.setCurrentIndex(0 if is_custom else 1)
            self.mode_options_stack.setVisible(is_custom)
            active = ("QPushButton { text-align: left; padding: 5px 12px; "
                      "border-radius: 6px; font-size: 12px; "
                      "border: 1px solid rgba(255,255,255,0.08); "
                      "background: rgba(255,255,255,0.08); "
                      "color: #f3f0e8; font-weight: 700; }")
            inactive = ("QPushButton { text-align: left; padding: 5px 12px; "
                        "border-radius: 6px; font-size: 12px; "
                        "border: 1px solid rgba(255,255,255,0.05); "
                        "background: rgba(255,255,255,0.04); "
                        "color: rgba(243,240,232,0.64); }")
            self.btn_tab_custom.setStyleSheet(active if is_custom else inactive)
            self.btn_tab_preset.setStyleSheet(inactive if is_custom else active)

        # ---- Data loading ----

        def _on_refresh_export_presets(self):
            self._log('Loading export presets...')
            try:
                presets = evoto.export.list_export_presets()
                self.export_preset_list.clear()
                for p in presets:
                    name = p.get(Field.NAME, 'unnamed')
                    uuid = p.get(ExportField.UUID, '')
                    item = QListWidgetItem(f'{name}  (uuid: {uuid})')
                    item.setData(Qt.UserRole, uuid)
                    self.export_preset_list.addItem(item)
                self._log(f'Loaded {self.export_preset_list.count()} export presets')
            except Exception as exc:
                self._log(f'Failed to load export presets: {exc}')

        # ---- Export ----

        def _on_start_export(self):
            pid = self.loader.project_id
            if not pid:
                themed_message(self, 'Error', 'Load a project first')
                return

            image_ids = (
                self.image_table.selected_image_ids()
                or self.image_table.all_image_ids()
                or list(self._image_ids)
                or list(self.loader.image_ids)
            )
            if not image_ids:
                themed_message(self, 'Error', 'Image IDs is required')
                return

            is_custom = self._current_export_mode() == 'custom'
            export_dir = self.export_dir_input.text().strip() if is_custom else ''
            if is_custom and not export_dir:
                themed_message(self, 'Error', 'Export directory is required')
                return

            listener_uuid = MY_LISTENER_UUID if self.chk_use_uuid.isChecked() else None

            if is_custom:
                self._do_custom_export(pid, export_dir, image_ids, listener_uuid)
            else:
                self._do_export_preset_export(pid, image_ids, listener_uuid)

        def _do_custom_export(self, project_id, export_dir, image_ids, listener_uuid):
            preset_suit_ids = self.preset_tree.selected_preset_ids()
            if not preset_suit_ids:
                themed_message(self, 'Error', 'Select at least one preset suit')
                return

            options = self._build_options()
            self._log(f'Calling export.startWithCustom:\n'
                      f'  project_id={project_id}\n'
                      f'  imageIds={len(image_ids)}\n'
                      f'  preset_suit_ids={preset_suit_ids}\n'
                      f'  options={pformat(options)}')

            try:
                result = evoto.export.start_with_custom(
                    project_id=project_id,
                    export_dir=export_dir,
                    preset_suit_ids=preset_suit_ids,
                    imageIds=image_ids,
                    export_listener_uuid=listener_uuid,
                    options=options,
                )
            except Exception as exc:
                self._log(f'export.startWithCustom failed: {exc}')
                themed_message(self, 'Export Failed', str(exc))
                return
            self._handle_export_result(result)

        def _do_export_preset_export(self, project_id, image_ids, listener_uuid):
            selected_items = self.export_preset_list.selectedItems()
            if not selected_items:
                themed_message(self, 'Error', 'Select at least one export preset')
                return

            export_preset_ids = [item.data(Qt.UserRole) for item in selected_items]
            self._log(f'Calling export.startWithExportPreset:\n'
                      f'  project_id={project_id}\n'
                      f'  imageIds={len(image_ids)}\n'
                      f'  export_preset_ids={export_preset_ids}')

            try:
                result = evoto.export.start_with_export_preset(
                    project_id=project_id,
                    export_preset_ids=export_preset_ids,
                    imageIds=image_ids,
                    export_listener_uuid=listener_uuid,
                )
            except Exception as exc:
                self._log(f'export.startWithExportPreset failed: {exc}')
                themed_message(self, 'Export Failed', str(exc))
                return
            self._handle_export_result(result)

        def _handle_export_result(self, result):
            self._log(f'Accepted:\n{pformat(result)}')
            dir_id = result.get(ExportField.EXPORT_DIR_ID)
            if dir_id:
                self._update_task_row(dir_id, {
                    Field.STATUS: 'running',
                    ExportField.PROGRESS: 0,
                    ExportField.REQUESTED_COUNT: result.get(ExportField.REQUESTED_COUNT, 0),
                    ExportField.COMPLETED_COUNT: 0,
                    ExportField.SUCCESS_COUNT: 0,
                    ExportField.FAILED_COUNT: 0,
                    ExportField.EXPORT_NAME: result.get(ExportField.EXPORT_NAME, ''),
                    ExportField.EXPORT_DIR: result.get(ExportField.EXPORT_DIR, ''),
                })

        # ---- Task table ----

        def _find_task_in_table(self, table, dir_id) -> int:
            for row in range(table.rowCount()):
                item = table.item(row, 0)
                if item and item.data(Qt.UserRole) == dir_id:
                    return row
            return -1

        def _remove_from_table(self, table, dir_id):
            row = self._find_task_in_table(table, dir_id)
            if row >= 0:
                table.removeRow(row)

        def _update_task_row(self, dir_id, info: dict):
            raw_status = info.get(Field.STATUS) or info.get(ExportField.STATE) or ''
            if raw_status in ('started', 'item_finished'):
                raw_status = 'running'
            status = raw_status
            fail_count = info.get(ExportField.FAILED_COUNT) or 0
            requested = info.get(ExportField.REQUESTED_COUNT) or 0
            completed_count = info.get(ExportField.COMPLETED_COUNT) or 0
            if requested > 0 and completed_count >= requested and status not in ('completed', 'failed'):
                status = 'completed'

            if self._find_task_in_table(self.completed_table, dir_id) >= 0:
                if status not in ('completed', 'failed'):
                    return

            is_fully_done = (status == 'completed' and fail_count == 0)
            target = self.completed_table if is_fully_done else self.exporting_table
            other = self.completed_table if target == self.exporting_table else self.exporting_table
            self._remove_from_table(other, dir_id)

            row = self._find_task_in_table(target, dir_id)
            is_new = row < 0
            if is_new:
                row = target.rowCount()
                target.insertRow(row)
                id_item = QTableWidgetItem(str(dir_id))
                id_item.setData(Qt.UserRole, dir_id)
                target.setItem(row, 0, id_item)

            ok_count = info.get(ExportField.SUCCESS_COUNT) or 0
            name = info.get(ExportField.EXPORT_NAME) or ''
            export_dir = info.get(ExportField.EXPORT_DIR) or ''

            if name:
                target.setItem(row, 1, QTableWidgetItem(str(name)))
            elif is_new:
                target.setItem(row, 1, QTableWidgetItem('-'))
            if requested > 0 or is_new:
                target.setItem(row, 2, QTableWidgetItem(f'{ok_count}/{requested} ok, {fail_count} fail'))
            if export_dir:
                target.setItem(row, 3, QTableWidgetItem(str(export_dir)))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(4)
            is_finished = status in ('completed', 'failed') or (requested > 0 and completed_count >= requested)
            if not is_finished:
                if status == 'paused':
                    btn = QPushButton('Resume')
                    btn.clicked.connect(lambda _, d=dir_id: self._action_resume(d))
                else:
                    btn = QPushButton('Pause')
                    btn.clicked.connect(lambda _, d=dir_id: self._action_pause(d))
                btn_layout.addWidget(btn)
            if is_finished and fail_count > 0:
                btn = QPushButton('Retry')
                btn.clicked.connect(lambda _, d=dir_id: self._action_retry(d))
                btn_layout.addWidget(btn)
            if is_finished and not fail_count:
                lbl = QLabel('Done')
                lbl.setProperty('ev_role', 'done')
                btn_layout.addWidget(lbl)
            btn_del = QPushButton('Delete')
            btn_del.setProperty('ev_role', 'danger')
            btn_del.clicked.connect(lambda _, d=dir_id: self._action_delete(d))
            btn_layout.addWidget(btn_del)
            target.setCellWidget(row, 4, btn_widget)

        def _action_pause(self, dir_id):
            try:
                evoto.export.pause(dir_id)
                self._log(f'Paused dir_id={dir_id}')
                self._on_query_all()
            except Exception as exc:
                self._log(f'Pause failed: {exc}')

        def _action_resume(self, dir_id):
            try:
                evoto.export.resume(dir_id)
                self._log(f'Resumed dir_id={dir_id}')
                self._on_query_all()
            except Exception as exc:
                self._log(f'Resume failed: {exc}')

        def _action_retry(self, dir_id):
            try:
                evoto.export.retry(dir_id)
                self._log(f'Retrying dir_id={dir_id}')
                self._on_query_all()
            except Exception as exc:
                self._log(f'Retry failed: {exc}')

        def _action_delete(self, dir_id):
            try:
                evoto.export.delete(dir_id)
                self._log(f'Deleted dir_id={dir_id}')
                self._remove_from_table(self.exporting_table, dir_id)
                self._remove_from_table(self.completed_table, dir_id)
            except Exception as exc:
                self._log(f'Delete failed: {exc}')

        def _on_query_all(self):
            try:
                if self.chk_use_uuid.isChecked():
                    result = evoto.export.query(export_listener_uuid=MY_LISTENER_UUID)
                else:
                    result = evoto.export.query()
                tasks = result.get(ExportField.ITEMS, [])
                self._log(f'Queried {len(tasks)} task(s)')
                returned_ids = set()
                for task in tasks:
                    dir_id = task.get(ExportField.EXPORT_DIR_ID)
                    if dir_id:
                        returned_ids.add(dir_id)
                        self._update_task_row(dir_id, task)
                for table in (self.exporting_table, self.completed_table):
                    for row in range(table.rowCount() - 1, -1, -1):
                        item = table.item(row, 0)
                        if item and item.data(Qt.UserRole) not in returned_ids:
                            table.removeRow(row)
            except Exception as exc:
                self._log(f'Query failed: {exc}')

        # ---- Events ----

        def _on_event_main(self, event_name: str, data: object):
            try:
                self._handle_event(event_name, data)
            except Exception as exc:
                self._log(f'Event handler error: {exc}')

        def _handle_event(self, event_name: str, data: object):
            payload = data if isinstance(data, dict) else {}
            dir_id = payload.get(ExportField.EXPORT_DIR_ID)

            status = payload.get(ExportField.STATE) or ''
            if not status and event_name == ExportCmd.COMPLETED:
                status = 'completed'
            elif not status and event_name == ExportCmd.FAILED:
                status = 'failed'

            if dir_id:
                self._update_task_row(dir_id, {
                    Field.STATUS: status,
                    ExportField.PROGRESS: payload.get(ExportField.PROGRESS, 0),
                    ExportField.REQUESTED_COUNT: payload.get(ExportField.REQUESTED_COUNT, 0),
                    ExportField.COMPLETED_COUNT: payload.get(ExportField.COMPLETED_COUNT, 0),
                    ExportField.SUCCESS_COUNT: payload.get(ExportField.SUCCESS_COUNT, 0),
                    ExportField.FAILED_COUNT: payload.get(ExportField.FAILED_COUNT, 0),
                    ExportField.EXPORT_NAME: payload.get(ExportField.EXPORT_NAME, ''),
                    ExportField.EXPORT_DIR: payload.get(ExportField.EXPORT_DIR, ''),
                })

            if event_name == ExportCmd.ITEM_FINISHED:
                item = payload.get(ExportField.ITEM, {})
                self._log(f'  item: uuid={item.get(ExportField.UUID)} '
                          f'id={item.get(ExportField.IMAGE_ID)} '
                          f'status={item.get(Field.STATUS)} '
                          f'output={item.get(ExportField.OUTPUT_PATH, "")}')
            else:
                self._log(f'{event_name}: dir_id={dir_id} state={status} '
                          f'progress={payload.get(ExportField.PROGRESS, 0)}')

        def closeEvent(self, event):
            evoto.shutdown()
            event.accept()


def main():
    if PYQT_IMPORT_ERROR is not None:
        raise RuntimeError("PySide6 is required") from PYQT_IMPORT_ERROR

    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = PresetExportDemoWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
