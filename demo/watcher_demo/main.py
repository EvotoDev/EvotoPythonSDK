"""Folder Watcher Demo - watch folders + multi-project export monitor."""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QGroupBox, QFileDialog,
    QCheckBox, QSpinBox, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame,
)
from PySide6.QtCore import Qt, Signal

import evoto
from demo.shared import ConnectBar, WatchConfigPanel, themed_message

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger('watcher_demo')

TICK_SVG = str(Path(__file__).resolve().parent.parent / 'preset_export_demo' / 'tick.svg')

_WINDOW_QSS = """
QWidget {
    background: #16181a; color: #f3f0e8; font-size: 12px;
}
QLabel {
    color: rgba(243, 240, 232, 0.78); background: transparent;
}
QLabel[ev_role="section-title"] {
    color: #f3f0e8; font-weight: 700; font-size: 11px;
    letter-spacing: 0.06em; background: transparent;
}
QLabel[ev_role="field-label"] {
    color: rgba(243, 240, 232, 0.50); font-size: 10px; background: transparent;
}
QLabel[ev_role="status-disconnected"],
QLabel[ev_role="status-connecting"],
QLabel[ev_role="status-connected"] {
    padding: 5px 10px; border-radius: 999px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.05); font-weight: 700;
}
QLabel[ev_role="status-disconnected"] { color: #ef8f8f; }
QLabel[ev_role="status-connecting"]   { color: #f0c548; }
QLabel[ev_role="status-connected"]    { color: #8fd7a7; }
QCheckBox {
    color: rgba(243, 240, 232, 0.88); spacing: 6px; background: transparent;
}
QCheckBox::indicator {
    min-width: 16px; max-width: 16px; min-height: 16px; max-height: 16px;
    border-radius: 2px; border: 1px solid #9c9d9f;
    background: rgba(255, 255, 255, 0.02);
}
QCheckBox::indicator:hover {
    border: 1px solid #3083ff; background: rgba(48, 131, 255, 0.10);
}
QCheckBox::indicator:checked {
    border: none; background: #3083ff; image: url(TICK_SVG_PATH);
}
QCheckBox::indicator:checked:hover { background: rgba(48, 131, 255, 0.55); }
QLineEdit, QTextEdit, QComboBox, QSpinBox, QTableWidget {
    background: #0000004d; border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 6px; color: #f3f0e8;
    selection-background-color: rgba(255, 255, 255, 0.10);
}
QLineEdit, QSpinBox { min-height: 28px; padding: 0 10px; }
QComboBox { min-height: 28px; padding: 0 34px 0 10px; }
QComboBox::drop-down {
    subcontrol-origin: padding; subcontrol-position: top right;
    border: none; width: 18px; background: transparent;
}
QTextEdit { padding: 8px; }
QHeaderView::section {
    background: rgba(255, 255, 255, 0.04); color: rgba(243, 240, 232, 0.72);
    border: none; border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    padding: 8px 10px; font-size: 11px; font-weight: 700;
}
QTableWidget { gridline-color: rgba(255, 255, 255, 0.04); }
QTableWidget::item { padding: 6px; background: transparent; }
QPushButton {
    min-height: 28px; padding: 0 10px; border-radius: 6px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    background: rgba(255, 255, 255, 0.06);
    color: rgba(243, 240, 232, 0.84); font-size: 12px; font-weight: 600;
}
QPushButton:hover  { background: rgba(255, 255, 255, 0.10); }
QPushButton:pressed { background: rgba(255, 255, 255, 0.14); }
QPushButton:disabled {
    background: rgba(255, 255, 255, 0.03);
    color: rgba(243, 240, 232, 0.30); border-color: rgba(255, 255, 255, 0.04);
}
QPushButton[ev_role="ghost"] {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.05);
    color: rgba(243, 240, 232, 0.72);
}
QPushButton[ev_role="ghost"]:hover { background: rgba(255, 255, 255, 0.08); }
QPushButton[ev_role="primary"] {
    background: #f0c548; color: #231a00;
    border: 1px solid rgba(240, 197, 72, 0.45); font-weight: 700;
    border-radius: 14px; padding: 0 16px;
}
QPushButton[ev_role="primary"]:hover { background: #f4cd62; }
QPushButton[ev_role="primary"]:disabled {
    background: rgba(240, 197, 72, 0.25); color: rgba(35, 26, 0, 0.5);
}
QFrame#panelCard {
    border: 1px solid rgba(255, 255, 255, 0.07); border-radius: 6px;
    background-color: #232629;
}
QSplitter::handle { background: #16181a; }
QScrollBar:vertical, QScrollBar:horizontal {
    background: #16181a; border-radius: 4px;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: rgba(255, 255, 255, 0.10); border-radius: 4px;
}
""".replace('TICK_SVG_PATH', TICK_SVG.replace('\\', '/'))


class WatcherDemoWindow(QWidget):
    files_received = Signal(dict)
    unexported_received = Signal(dict)

    def __init__(self):
        super().__init__()
        self._watch_paths: list[str] = []
        self._watch_running = False
        self._include_sub = False
        self._current_project_id: int | None = None
        self.files_received.connect(self._on_files_received_main)
        self.unexported_received.connect(self._on_unexported_received_main)
        self._init_ui()
        self.setStyleSheet(_WINDOW_QSS)

    def _init_ui(self):
        self.setWindowTitle('Watcher Demo')
        self.resize(1100, 720)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self.connect_bar = ConnectBar(title='Watcher Demo')
        self.connect_bar.connected.connect(self._on_connected)
        self.connect_bar.disconnected.connect(self._on_disconnected)
        self.connect_bar.connection_failed.connect(self._on_connect_failed)
        root.addWidget(self.connect_bar)

        body = QHBoxLayout()
        body.setSpacing(12)

        # ── Left column: config panels ──
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # ---- Watch Folders panel (shared widget) ----
        self.watch_panel = WatchConfigPanel(title='WATCH FOLDERS')
        self.btn_toggle_watch = QPushButton('Start Watch')
        self.btn_toggle_watch.setProperty('ev_role', 'primary')
        self.btn_toggle_watch.setEnabled(False)
        self.btn_toggle_watch.clicked.connect(self._on_toggle_watch)
        self.watch_panel.add_header_action(self.btn_toggle_watch)
        self.btn_refresh_watch = self.watch_panel.btn_refresh
        self.watch_panel.refresh_requested.connect(self._refresh_watch_status)
        left_layout.addWidget(self.watch_panel, 1)

        # ---- Export Monitor panel ----
        mon_panel = QFrame()
        mon_panel.setObjectName('panelCard')
        mon_panel.setFrameShape(QFrame.StyledPanel)
        mp_inner = QVBoxLayout(mon_panel)
        mp_inner.setContentsMargins(12, 10, 12, 12)
        mp_inner.setSpacing(8)

        mp_head = QHBoxLayout()
        mp_title = QLabel('EXPORT MONITORS')
        mp_title.setProperty('ev_role', 'section-title')
        mp_head.addWidget(mp_title)
        mp_head.addStretch()
        self.btn_refresh_monitors = QPushButton('Refresh')
        self.btn_refresh_monitors.setProperty('ev_role', 'ghost')
        self.btn_refresh_monitors.setEnabled(False)
        self.btn_refresh_monitors.clicked.connect(self._on_refresh_monitors)
        mp_head.addWidget(self.btn_refresh_monitors)
        mp_inner.addLayout(mp_head)

        interval_row = QHBoxLayout()
        interval_row.setSpacing(6)
        lbl_interval = QLabel('Interval')
        lbl_interval.setProperty('ev_role', 'field-label')
        interval_row.addWidget(lbl_interval)
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(1, 3600)
        self.spin_interval.setValue(30)
        self.spin_interval.setFixedWidth(80)
        interval_row.addWidget(self.spin_interval)
        self.combo_unit = QComboBox()
        self.combo_unit.addItem('sec', 's')
        self.combo_unit.addItem('min', 'm')
        self.combo_unit.setFixedWidth(90)
        interval_row.addWidget(self.combo_unit)
        interval_row.addStretch()
        mp_inner.addLayout(interval_row)

        add_mon_row = QHBoxLayout()
        add_mon_row.setSpacing(6)
        lp = QLabel('Project')
        lp.setProperty('ev_role', 'field-label')
        add_mon_row.addWidget(lp)
        self.mon_project_input = QLineEdit()
        self.mon_project_input.setPlaceholderText('Project ID')
        self.mon_project_input.setFixedWidth(100)
        add_mon_row.addWidget(self.mon_project_input)
        self.btn_load_project = QPushButton('Current')
        self.btn_load_project.setProperty('ev_role', 'ghost')
        self.btn_load_project.setEnabled(False)
        self.btn_load_project.clicked.connect(self._on_load_project)
        add_mon_row.addWidget(self.btn_load_project)
        add_mon_row.addStretch()
        btn_add_mon = QPushButton('Add Monitor')
        btn_add_mon.clicked.connect(self._on_add_monitor)
        add_mon_row.addWidget(btn_add_mon)
        mp_inner.addLayout(add_mon_row)

        self.monitor_table = QTableWidget(0, 2)
        self.monitor_table.setHorizontalHeaderLabels(['Project', ''])
        mh = self.monitor_table.horizontalHeader()
        mh.setSectionResizeMode(0, QHeaderView.Stretch)
        mh.setSectionResizeMode(1, QHeaderView.Fixed)
        mh.resizeSection(1, 90)
        self.monitor_table.verticalHeader().setVisible(False)
        self.monitor_table.verticalHeader().setDefaultSectionSize(36)
        self.monitor_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.monitor_table.setSelectionBehavior(QTableWidget.SelectRows)
        mp_inner.addWidget(self.monitor_table)

        mon_actions = QHBoxLayout()
        mon_actions.addStretch()
        self.btn_stop_all_mon = QPushButton('Start All')
        self.btn_stop_all_mon.setProperty('ev_role', 'primary')
        self.btn_stop_all_mon.setEnabled(False)
        self.btn_stop_all_mon.clicked.connect(self._on_toggle_all_monitors)
        mon_actions.addWidget(self.btn_stop_all_mon)
        mp_inner.addLayout(mon_actions)

        left_layout.addWidget(mon_panel, 1)
        body.addWidget(left, 1)

        # ── Right column: log + unexported ──
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Events log
        log_panel = QFrame()
        log_panel.setObjectName('panelCard')
        log_panel.setFrameShape(QFrame.StyledPanel)
        lp_inner = QVBoxLayout(log_panel)
        lp_inner.setContentsMargins(12, 10, 12, 12)
        lp_inner.setSpacing(8)
        lp_head = QHBoxLayout()
        lp_title = QLabel('EVENTS LOG')
        lp_title.setProperty('ev_role', 'section-title')
        lp_head.addWidget(lp_title)
        lp_head.addStretch()
        self.lbl_file_count = QLabel('0 files')
        self.lbl_file_count.setProperty('ev_role', 'field-label')
        lp_head.addWidget(self.lbl_file_count)
        btn_clear = QPushButton('Clear')
        btn_clear.setProperty('ev_role', 'ghost')
        btn_clear.clicked.connect(lambda: (self.log_view.clear(), self._reset_count()))
        lp_head.addWidget(btn_clear)
        lp_inner.addLayout(lp_head)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(
            'font-family: Menlo, Monaco, Consolas, monospace; font-size: 12px; '
            'background-color: #0a0a0a; color: #d8d8d8; '
            'border: 1px solid rgba(255, 255, 255, 0.05); '
            'border-radius: 6px; padding: 6px;')
        lp_inner.addWidget(self.log_view)
        right_layout.addWidget(log_panel, 1)

        # Unexported images
        unexp_panel = QFrame()
        unexp_panel.setObjectName('panelCard')
        unexp_panel.setFrameShape(QFrame.StyledPanel)
        up_inner = QVBoxLayout(unexp_panel)
        up_inner.setContentsMargins(12, 10, 12, 12)
        up_inner.setSpacing(8)
        up_head = QHBoxLayout()
        up_title = QLabel('UNEXPORTED IMAGES')
        up_title.setProperty('ev_role', 'section-title')
        up_head.addWidget(up_title)
        up_head.addStretch()
        up_inner.addLayout(up_head)

        up_ctrl = QHBoxLayout()
        up_ctrl.setSpacing(8)
        lbl_proj = QLabel('Project')
        lbl_proj.setProperty('ev_role', 'field-label')
        up_ctrl.addWidget(lbl_proj)
        self.combo_unexported_project = QComboBox()
        self.combo_unexported_project.setMinimumWidth(200)
        up_ctrl.addWidget(self.combo_unexported_project, 1)
        self.btn_list_unexported = QPushButton('Query')
        self.btn_list_unexported.setProperty('ev_role', 'ghost')
        self.btn_list_unexported.setEnabled(False)
        self.btn_list_unexported.clicked.connect(self._on_list_unexported)
        up_ctrl.addWidget(self.btn_list_unexported)
        self.btn_mark_exported = QPushButton('Mark All Exported')
        self.btn_mark_exported.setProperty('ev_role', 'ghost')
        self.btn_mark_exported.setEnabled(False)
        self.btn_mark_exported.clicked.connect(self._on_mark_all_exported)
        up_ctrl.addWidget(self.btn_mark_exported)
        up_inner.addLayout(up_ctrl)

        self.unexported_table = QTableWidget(0, 3)
        self.unexported_table.setHorizontalHeaderLabels(
            ['ID', 'Filename', 'Path'])
        uh = self.unexported_table.horizontalHeader()
        uh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        uh.setSectionResizeMode(1, QHeaderView.Stretch)
        uh.setSectionResizeMode(2, QHeaderView.Stretch)
        self.unexported_table.verticalHeader().setVisible(False)
        self.unexported_table.verticalHeader().setDefaultSectionSize(36)
        self.unexported_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.unexported_table.setSelectionBehavior(QTableWidget.SelectRows)
        up_inner.addWidget(self.unexported_table)
        right_layout.addWidget(unexp_panel, 1)

        body.addWidget(right, 1)
        root.addLayout(body, 1)
        self._total_files = 0

    def _log(self, msg: str):
        ts = datetime.now().strftime('%H:%M:%S')
        self.log_view.append(f'[{ts}] {msg}')
        logger.info(msg)

    def _reset_count(self):
        self._total_files = 0
        self.lbl_file_count.setText('0 files')

    # ── Connection ──
    # Connection state is owned by ConnectBar: user-initiated Disconnect,
    # host crash, and host.quit all fire its `disconnected` signal. The
    # slots below only react to that signal with demo-local widget updates.

    def _on_connected(self):
        self.btn_toggle_watch.setEnabled(True)
        self.btn_refresh_watch.setEnabled(True)
        self.btn_load_project.setEnabled(True)
        self.btn_refresh_monitors.setEnabled(True)
        self.btn_stop_all_mon.setEnabled(True)
        self.btn_list_unexported.setEnabled(True)
        self.btn_mark_exported.setEnabled(True)
        self._log('Connected')
        evoto.watcher.on_files_added(self._on_files_event)
        evoto.watcher.on_unexported_found(self._on_unexported_event)
        self._refresh_watch_status()
        self._on_refresh_monitors()

    def _on_disconnected(self):
        self.btn_toggle_watch.setEnabled(False)
        self.btn_refresh_watch.setEnabled(False)
        self.btn_load_project.setEnabled(False)
        self.btn_refresh_monitors.setEnabled(False)
        self.btn_stop_all_mon.setEnabled(False)
        self.btn_list_unexported.setEnabled(False)
        self.btn_mark_exported.setEnabled(False)
        self._log('Disconnected')

    def _on_connect_failed(self, reason: str):
        # Surface the real host-side rejection reason (e.g. 409 Conflict /
        # 403 Forbidden) in the UI log so users see more than just "Failed".
        self._log(f'Connect failed: {reason}')

    # ── Watch folders (table-driven) ──

    def _set_watch_status(self, running: bool):
        self._watch_running = running
        if running:
            self.btn_toggle_watch.setText('Stop Watch')
            self.btn_toggle_watch.setProperty('ev_role', '')
        else:
            self.btn_toggle_watch.setText('Start Watch')
            self.btn_toggle_watch.setProperty('ev_role', 'primary')
        self.btn_toggle_watch.style().unpolish(self.btn_toggle_watch)
        self.btn_toggle_watch.style().polish(self.btn_toggle_watch)

    def _refresh_watch_status(self):
        try:
            watchers = evoto.watcher.list()
            self._log(f'watch.list returned: {watchers}')
            if watchers:
                w = watchers[0]
                self._watch_paths = list(w.get('paths', []))
                self.watch_panel.set_paths(self._watch_paths)
                self.watch_panel.set_include_sub_dir(w.get('includeSubDir', False))
                self._set_watch_status(w.get('running', False))
                self._log(
                    f'Watch status: running={w.get("running")}, '
                    f'{len(self._watch_paths)} paths, '
                    f'subdir={w.get("includeSubDir", False)}')
            else:
                self._watch_paths.clear()
                self.watch_panel.set_paths([])
                self._set_watch_status(False)
                self._log('Watch status: no active watcher')
        except Exception as e:
            self._set_watch_status(False)
            self._log(f'Refresh watch status failed: {e}')

    def _on_toggle_watch(self):
        if self._watch_running:
            try:
                evoto.watcher.stop()
                self._log('Watch stopped')
                self.watch_panel.set_editable(True)
                self._refresh_watch_status()
            except Exception as e:
                self._log(f'Stop failed: {e}')
        else:
            paths = self.watch_panel.paths()
            if not paths:
                self._log('Add at least one folder first')
                return
            self._watch_paths = paths
            self._include_sub = self.watch_panel.include_sub_dir()
            filters = self.watch_panel.filters() or None
            try:
                result = evoto.watcher.start(
                    paths=self._watch_paths,
                    filters=filters,
                    include_sub_dir=self._include_sub,
                )
                wid = result.get('watchId', '')[:8]
                self._log(
                    f'Watch started: {len(self._watch_paths)} paths, '
                    f'filters={filters or "all"}, id={wid}...')
                self.watch_panel.set_editable(False)
                self._refresh_watch_status()
            except Exception as e:
                self._log(f'Start failed: {e}')

    # ── Export monitor (table-driven, multi-project) ──

    def _on_load_project(self):
        try:
            result = evoto.project.current()
            proj = result.get('project', {})
            self._current_project_id = proj.get('id')
            self.mon_project_input.setText(str(proj.get('id', '')))
            self._log(f'Current project: id={proj.get("id")} name={proj.get("name")}')
        except Exception as e:
            self._log(f'Failed to load project: {e}')

    def _on_add_monitor(self):
        pid_text = self.mon_project_input.text().strip()
        if not pid_text:
            themed_message(self, 'Hint', 'Enter a Project ID')
            return
        try:
            result = evoto.watcher.start_export_monitor(
                project_id=int(pid_text),
                interval=self.spin_interval.value(),
                unit=self.combo_unit.currentData(),
            )
            total = result.get('total_monitors', 0)
            self._log(f'Monitor added: project={pid_text}, total={total}')
            self._on_refresh_monitors()
        except Exception as e:
            self._log(f'Add monitor failed: {e}')

    def _on_remove_monitor(self, project_id: int):
        try:
            evoto.watcher.stop_export_monitor(project_id=project_id)
            self._log(f'Monitor removed: project={project_id}')
            self._on_refresh_monitors()
        except Exception as e:
            self._log(f'Remove monitor failed: {e}')

    def _resolve_project_name(self, project_id: int) -> str:
        try:
            result = evoto.project.info(project_id)
            proj = result.get('project', result)
            name = proj.get('name', '')
            if name:
                return f'{name} ({project_id})'
        except Exception as e:
            self._log(f'Resolve project name failed for {project_id}: {e}')
        return str(project_id)

    def _update_monitor_button(self, running: bool):
        if running:
            self.btn_stop_all_mon.setText('Stop All')
            self.btn_stop_all_mon.setProperty('ev_role', '')
        else:
            self.btn_stop_all_mon.setText('Start All')
            self.btn_stop_all_mon.setProperty('ev_role', 'primary')
        self.btn_stop_all_mon.style().unpolish(self.btn_stop_all_mon)
        self.btn_stop_all_mon.style().polish(self.btn_stop_all_mon)

    def _on_refresh_monitors(self):
        try:
            result = evoto.watcher.query_export_monitor()
            project_ids = result.get('project_ids', [])
            interval = result.get('interval', 30)
            unit = result.get('unit', 's')
            timer_running = result.get('running', False)

            self.spin_interval.setValue(interval)
            idx_unit = self.combo_unit.findData(unit)
            if idx_unit >= 0:
                self.combo_unit.setCurrentIndex(idx_unit)

            self.monitor_table.setRowCount(0)
            prev_selected = self.combo_unexported_project.currentData()
            self.combo_unexported_project.clear()

            for pid_val in project_ids:
                pid = int(pid_val)
                row = self.monitor_table.rowCount()
                self.monitor_table.insertRow(row)
                display = self._resolve_project_name(pid)
                self.monitor_table.setItem(row, 0, QTableWidgetItem(display))
                btn = QPushButton('Remove')
                btn.setProperty('ev_role', 'ghost')
                btn.clicked.connect(
                    lambda _, p=pid: self._on_remove_monitor(p))
                self.monitor_table.setCellWidget(row, 1, btn)
                self.combo_unexported_project.addItem(display, pid)

            if prev_selected is not None:
                idx = self.combo_unexported_project.findData(prev_selected)
                if idx >= 0:
                    self.combo_unexported_project.setCurrentIndex(idx)

            self._update_monitor_button(len(project_ids) > 0 and timer_running)
            self._log(
                f'Monitors: {len(project_ids)} projects, '
                f'interval={interval}{unit}, '
                f'timer={"running" if timer_running else "stopped"}')
        except Exception as e:
            self._log(f'Refresh monitors failed: {e}')

    def _on_toggle_all_monitors(self):
        if self.btn_stop_all_mon.text() == 'Stop All':
            try:
                result = evoto.watcher.stop_export_monitor()
                stopped = result.get('stopped_count', 0)
                self._log(f'Stopped {stopped} monitors')
                self._on_refresh_monitors()
            except Exception as e:
                self._log(f'Stop all failed: {e}')
        else:
            self._on_restart_all_monitors()

    def _on_restart_all_monitors(self):
        rows = self.monitor_table.rowCount()
        if rows == 0:
            self._log('No projects to start')
            return
        for r in range(rows):
            item = self.monitor_table.item(r, 0)
            if not item:
                continue
            text = item.text()
            pid_str = text.split('(')[-1].rstrip(')') if '(' in text else text
            try:
                pid = int(pid_str)
                evoto.watcher.start_export_monitor(
                    project_id=pid,
                    interval=self.spin_interval.value(),
                    unit=self.combo_unit.currentData(),
                )
            except Exception as e:
                self._log(f'Start monitor {pid_str} failed: {e}')
        self._on_refresh_monitors()

    # ── Unexported images ──

    def _get_selected_project_id(self) -> int | None:
        pid = self.combo_unexported_project.currentData()
        if pid is None or pid <= 0:
            themed_message(self, 'Hint', 'Select a project from the dropdown')
            return None
        return int(pid)

    def _on_list_unexported(self):
        pid = self._get_selected_project_id()
        if pid is None:
            return
        try:
            images = evoto.watcher.list_unexported(pid)
            self._populate_unexported_table(images)
            self._log(f'Found {len(images)} unexported in project {pid}')
        except Exception as e:
            self._log(f'List unexported failed: {e}')

    def _on_mark_all_exported(self):
        pid = self._get_selected_project_id()
        if pid is None:
            return
        try:
            images = evoto.watcher.list_unexported(pid)
            if not images:
                self._log('No unexported images')
                return
            image_ids = [img.get('id') for img in images if img.get('id')]
            result = evoto.watcher.mark_exported(image_ids=image_ids)
            self._log(f'Marked {result.get("updated_count", 0)} images')
            self._on_list_unexported()
        except Exception as e:
            self._log(f'Mark exported failed: {e}')

    def _populate_unexported_table(self, images: list):
        self.unexported_table.setRowCount(0)
        for img in images:
            row = self.unexported_table.rowCount()
            self.unexported_table.insertRow(row)
            self.unexported_table.setItem(
                row, 0, QTableWidgetItem(str(img.get('id', ''))))
            self.unexported_table.setItem(
                row, 1, QTableWidgetItem(str(img.get('filename', ''))))
            self.unexported_table.setItem(
                row, 2, QTableWidgetItem(str(img.get('absolute_path', ''))))

    # ── Events (thread-safe) ──

    def _on_files_event(self, data: dict):
        self.files_received.emit(data)

    def _on_files_received_main(self, data: dict):
        files = data.get('files', [])
        wid = data.get('watchId', '')[:8]
        self._total_files += len(files)
        self.lbl_file_count.setText(f'{self._total_files} files')
        for f in files:
            self._log(f'[{wid}] new: {f}')

    def _on_unexported_event(self, data: dict):
        self.unexported_received.emit(data)

    def _on_unexported_received_main(self, data: dict):
        images = data.get('images', [])
        pid = data.get('project_id', '?')
        self._log(f'Unexported event: project={pid}, {len(images)} images')
        self._populate_unexported_table(images)

    def closeEvent(self, event):
        evoto.shutdown()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = WatcherDemoWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
