"""Hot Folder Workflow Demo - window entry point.

Layout
------
┌─ Top bar ──────────────────────────────────────────────────────────┐
│ Title  │   Connect status │ Connect/Disconnect                     │
├─ Project bar ──────────────────────────────────────────────────────┤
│ Project: [-] [Select] [Create]                                     │
│ Watcher: [✓] Include sub-dirs   Filters [JPG ▾] │ [Start] [Stop]   │
├─ MAPPINGS ─────────────────────────────────────────────[+ Add Row]─┤
│ mapping_table (On / Label / Watch / Export / Preset / Options /...) │
├─ Events Log ───────────────────────────────────────────────────────┤
│ [hh:mm:ss] ...                                                     │
└────────────────────────────────────────────────────────────────────┘

Configuration is autosaved to ``demo/hot_folder_demo/config/config.json``
so the demo picks up right where it left off - no manual load/save step.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFrame,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QSplitter, QTextEdit, QVBoxLayout, QWidget,
)

import evoto

from demo.shared import ConnectBar, WatchConfigPanel, apply_theme, themed_message

from demo.hot_folder_demo.config import DEFAULT_CONFIG_PATH, HotFolderConfig, MappingRow
from demo.hot_folder_demo.launcher import EvotoLauncher
from demo.hot_folder_demo.mapping_table import MappingTable
from demo.hot_folder_demo.pipeline import Pipeline


logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger('hot_folder_demo')


class ProjectPickerDialog(QDialog):
    """Tiny dialog to pick an existing project from a flat list."""

    def __init__(self, projects: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle('Select Project')
        self.setModal(True)
        self.resize(420, 480)

        self._selected: dict | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        lbl = QLabel('Pick the Evoto project shared by all lanes.')
        lbl.setProperty('ev_role', 'section-caption')
        root.addWidget(lbl)

        self.list = QListWidget()
        for p in projects:
            text = f'#{p.get("id") or p.get("project_id")} - {p.get("name", "")}'
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, p)
            self.list.addItem(item)
        self.list.itemDoubleClicked.connect(lambda _: self._accept())
        root.addWidget(self.list, 1)

        btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        btns.button(QDialogButtonBox.Ok).setProperty('ev_role', 'primary')
        root.addWidget(btns)

        apply_theme(self)

    def _accept(self):
        item = self.list.currentItem()
        if not item:
            return
        self._selected = item.data(Qt.UserRole)
        self.accept()

    def selection(self) -> dict | None:
        return self._selected


class HotFolderDemoWindow(QWidget):
    """Main window composing the top bar, mapping table, and log panel."""

    log_received = Signal(str)

    def __init__(self):
        super().__init__()
        self._config = HotFolderConfig()
        self._config_path = DEFAULT_CONFIG_PATH
        self._pipeline = Pipeline(self._config, parent=self)

        # Debounced autosave so label keystrokes don't hammer the disk.
        # A short idle window collapses bursts of UI signals into one
        # JSON write.
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(300)
        self._save_timer.timeout.connect(self._save_now)
        self._autosave_enabled = False

        # Child-process launcher + auto-reconnect timer. The timer
        # polls ``evoto.connect()`` via the ConnectBar on a 2 s
        # cadence while we're waiting for the just-spawned Evoto to
        # finish booting. 30 attempts ≈ 60 s is plenty even for a cold
        # start from disk.
        self._launcher = EvotoLauncher(self)
        self._launcher.log.connect(self._append_log)
        self._launcher.exited.connect(self._on_evoto_exited)
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setInterval(2000)
        self._reconnect_timer.timeout.connect(self._try_auto_connect)
        self._reconnect_attempts_left = 0

        self.log_received.connect(self._append_log)
        self._pipeline.log.connect(self._append_log)
        self._pipeline.row_status.connect(self._on_row_status)

        self._init_ui()
        apply_theme(self)

        self._auto_load()
        self._refresh_header()
        # Only arm autosave *after* initial load so loading existing
        # state doesn't round-trip through ``_save_now`` immediately.
        self._autosave_enabled = True

        # Kick off the auto-launch flow once the UI is settled so any
        # error dialog has a parent window to attach to. Keep this
        # completely independent from ``connect_bar`` state: the user
        # asked for these controls to stay live whether or not the
        # plugin is connected.
        QTimer.singleShot(0, self._maybe_auto_launch)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _init_ui(self):
        self.setWindowTitle('Hot Folder Workflow Demo')
        self.resize(1320, 820)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        root.addLayout(self._build_title_bar())

        # Two-level layout:
        # - Top: horizontal splitter with the three config cards on the
        #   left and the events log on the right (log takes roughly a
        #   third of the width).
        # - Bottom: the mappings table full-width.
        # We wrap both in a vertical splitter so the user can grow the
        # table when they have many lanes, or the log when they're
        # debugging an export.
        top_left = QWidget()
        top_left_lay = QVBoxLayout(top_left)
        top_left_lay.setContentsMargins(0, 0, 0, 0)
        top_left_lay.setSpacing(12)
        top_left_lay.addWidget(self._build_launcher_bar())
        top_left_lay.addWidget(self._build_project_bar())
        top_left_lay.addWidget(self._build_watcher_bar())
        top_left_lay.addStretch(1)

        top_split = QSplitter(Qt.Horizontal)
        top_split.setChildrenCollapsible(False)
        top_split.addWidget(top_left)
        top_split.addWidget(self._build_log_panel())
        top_split.setStretchFactor(0, 2)
        top_split.setStretchFactor(1, 1)
        top_split.setSizes([860, 420])

        main_split = QSplitter(Qt.Vertical)
        main_split.setChildrenCollapsible(False)
        main_split.addWidget(top_split)
        main_split.addWidget(self._build_mappings_panel())
        main_split.setStretchFactor(0, 3)
        main_split.setStretchFactor(1, 2)
        main_split.setSizes([480, 300])
        root.addWidget(main_split, 1)

    def _build_title_bar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        title = QLabel('Hot Folder Workflow')
        f = QFont(); f.setPointSize(15); f.setBold(True)
        title.setFont(f)
        title.setStyleSheet('color: #f3f0e8;')
        row.addWidget(title)
        row.addStretch()

        self.connect_bar = ConnectBar()
        self.connect_bar.connected.connect(self._on_connected)
        self.connect_bar.disconnected.connect(self._on_disconnected)
        self.connect_bar.connection_failed.connect(self._on_connect_failed)
        row.addWidget(self.connect_bar)
        return row

    def _build_launcher_bar(self) -> QFrame:
        """Panel controlling an optional locally-spawned Evoto child.

        The widgets inside are intentionally *not* disabled by the
        plugin's connect state - booting Evoto is what makes a
        connection possible in the first place, so gating it on that
        same state would deadlock the UI.
        """
        frame = QFrame()
        frame.setObjectName('panelCard')
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)

        head = QHBoxLayout()
        head.addWidget(_section_label('EVOTO LAUNCHER'))
        self.launcher_status = QLabel('not running')
        self.launcher_status.setProperty('ev_role', 'section-caption')
        head.addWidget(self.launcher_status)
        head.addStretch()

        self.chk_auto_launch = QCheckBox('Auto-launch on start')
        self.chk_auto_launch.setToolTip(
            'Start Evoto in the background every time this demo opens '
            'and retry-connect until the host is up.')
        self.chk_auto_launch.toggled.connect(self._on_auto_launch_toggled)
        head.addWidget(self.chk_auto_launch)

        self.btn_launch = QPushButton('Launch Evoto')
        self.btn_launch.setProperty('ev_role', 'ghost')
        self.btn_launch.clicked.connect(self._on_toggle_launch)
        head.addWidget(self.btn_launch)
        lay.addLayout(head)

        path_row = QHBoxLayout()
        path_lbl = QLabel('Path:')
        path_lbl.setProperty('ev_role', 'section-caption')
        path_row.addWidget(path_lbl)
        self.evoto_path_edit = QLineEdit()
        self.evoto_path_edit.setPlaceholderText(
            '/Applications/Evoto.app'
            if sys.platform == 'darwin'
            else r'C:\Program Files\Evoto\Evoto.exe'
            if sys.platform == 'win32'
            else '/opt/evoto/bin/Evoto')
        self.evoto_path_edit.editingFinished.connect(self._on_evoto_path_edited)
        path_row.addWidget(self.evoto_path_edit, 1)
        self.btn_browse_evoto = QPushButton('Browse...')
        self.btn_browse_evoto.setProperty('ev_role', 'ghost')
        self.btn_browse_evoto.clicked.connect(self._on_pick_evoto_path)
        path_row.addWidget(self.btn_browse_evoto)
        lay.addLayout(path_row)

        return frame

    def _build_project_bar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName('panelCard')
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)

        lay.addWidget(_section_label('PROJECT'))
        self.project_label = QLabel('-')
        self.project_label.setStyleSheet('color: #f3f0e8; font-weight: 600;')
        lay.addWidget(self.project_label, 1)

        self.btn_select_project = QPushButton('Select...')
        self.btn_select_project.setProperty('ev_role', 'ghost')
        self.btn_select_project.setEnabled(False)
        self.btn_select_project.clicked.connect(self._on_select_project)
        lay.addWidget(self.btn_select_project)

        self.btn_create_project = QPushButton('Create...')
        self.btn_create_project.setProperty('ev_role', 'ghost')
        self.btn_create_project.setEnabled(False)
        self.btn_create_project.clicked.connect(self._on_create_project)
        lay.addWidget(self.btn_create_project)

        return frame

    def _build_watcher_bar(self) -> QFrame:
        """Reusable ``WatchConfigPanel`` - folders table, subdir and filters.

        Folders live globally here (one source of truth for
        ``watcher.start(paths=...)``). Each mapping row references one
        of these paths through a combo box, so adding / removing a
        folder in this panel flows straight to the table.
        """
        self.watch_panel = WatchConfigPanel(title='WATCHER')

        # Single toggle button: flips between "Start All" (primary) and
        # "Stop All" (ghost) based on whether the pipeline is running.
        # The role property is swapped at runtime in ``_refresh_header``
        # and we re-polish the widget so the QSS picks up the new role.
        self.btn_run = QPushButton('Start All')
        self.btn_run.setProperty('ev_role', 'primary')
        self.btn_run.setEnabled(False)
        self.btn_run.clicked.connect(self._on_toggle_run)
        self.watch_panel.add_header_action(self.btn_run)

        self.watch_panel.paths_changed.connect(self._on_watch_paths_changed)
        self.watch_panel.settings_changed.connect(self._on_watcher_changed)
        self.watch_panel.refresh_requested.connect(self._on_refresh_watch_status)
        return self.watch_panel

    def _build_mappings_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName('panelCard')
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(8)

        head = QHBoxLayout()
        title = _section_label('MAPPINGS')
        head.addWidget(title)
        self.mapping_hint = QLabel(
            'Each row defines one lane. Watcher picks up new files under '
            '"Watch Folder", the host imports them into the shared project, '
            'and the plugin groups the resulting image IDs by row + sub-dir '
            'and runs a custom-preset export to "Export Folder".')
        self.mapping_hint.setWordWrap(True)
        self.mapping_hint.setProperty('ev_role', 'section-caption')
        head.addWidget(self.mapping_hint, 1)
        head.addStretch()

        self.btn_add_row = QPushButton('+ Add Row')
        self.btn_add_row.setProperty('ev_role', 'ghost')
        self.btn_add_row.clicked.connect(self._on_add_row)
        head.addWidget(self.btn_add_row)
        lay.addLayout(head)

        self.table = MappingTable()
        self.table.rows_changed.connect(self._on_rows_changed)
        lay.addWidget(self.table, 1)

        return frame

    def _build_log_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName('panelCard')
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(8)

        head = QHBoxLayout()
        head.addWidget(_section_label('EVENTS LOG'))
        head.addStretch()
        btn_clear = QPushButton('Clear')
        btn_clear.setProperty('ev_role', 'ghost')
        head.addWidget(btn_clear)
        lay.addLayout(head)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(
            'font-family: Menlo, Monaco, Consolas, monospace; '
            'background-color: #0a0a0a; color: #d8d8d8; '
            'border: 1px solid rgba(255, 255, 255, 0.05); '
            'border-radius: 6px; padding: 6px;')
        btn_clear.clicked.connect(self.log_view.clear)
        lay.addWidget(self.log_view)

        return frame

    # ------------------------------------------------------------------
    # Header / state sync
    # ------------------------------------------------------------------

    def _refresh_header(self) -> None:
        p = self._config.project
        if p.id:
            self.project_label.setText(f'#{p.id} - {p.name or "(unnamed)"}')
        else:
            self.project_label.setText('-')

        # Launcher panel - reflect config + live subprocess state. The
        # guards prevent re-entrancy when we programmatically seed the
        # widgets during ``_auto_load``.
        self.evoto_path_edit.blockSignals(True)
        self.evoto_path_edit.setText(self._config.launcher.evoto_path)
        self.evoto_path_edit.blockSignals(False)
        self.chk_auto_launch.blockSignals(True)
        self.chk_auto_launch.setChecked(self._config.launcher.auto_launch)
        self.chk_auto_launch.blockSignals(False)
        self._refresh_launch_button()

        self.watch_panel.set_include_sub_dir(self._config.watcher.include_sub_dir)
        self.watch_panel.set_filters(self._config.watcher.filters)
        self.watch_panel.set_paths(self._config.watcher.paths)
        self.table.set_watch_paths(self._config.watcher.paths)

        running = self._pipeline.is_running()
        connected = self.connect_bar.is_connected()
        if running:
            self.btn_run.setText('Stop All')
            self.btn_run.setProperty('ev_role', 'ghost')
            self.btn_run.setEnabled(True)
        else:
            self.btn_run.setText('Start All')
            self.btn_run.setProperty('ev_role', 'primary')
            self.btn_run.setEnabled(connected)
        # Re-polish so the swapped ``ev_role`` triggers a QSS restyle
        # (style selectors keyed on property values only re-evaluate
        # when the style is explicitly re-applied).
        style = self.btn_run.style()
        style.unpolish(self.btn_run)
        style.polish(self.btn_run)
        self.watch_panel.set_refresh_enabled(connected)

    def _pull_from_ui(self) -> None:
        """Snapshot widget state back into self._config before save/start."""
        self._config.mappings = self.table.rows()
        self._config.watcher.paths = self.watch_panel.paths()
        self._config.watcher.include_sub_dir = self.watch_panel.include_sub_dir()
        self._config.watcher.filters = self.watch_panel.filters()

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _on_connected(self):
        self._append_log('Connected to host')
        self.btn_select_project.setEnabled(True)
        self.btn_create_project.setEnabled(True)
        # Handshake succeeded -> no further retries needed.
        self._reconnect_timer.stop()
        self._reconnect_attempts_left = 0
        self._refresh_header()

    def _on_disconnected(self):
        self._pipeline.stop()
        self._append_log('Disconnected')
        self.btn_select_project.setEnabled(False)
        self.btn_create_project.setEnabled(False)
        # A manual disconnect cancels any in-flight auto-reconnect so
        # we don't fight the user by silently reconnecting.
        self._reconnect_timer.stop()
        self._reconnect_attempts_left = 0
        self._refresh_header()

    def _on_connect_failed(self, reason: str):
        # Surface the real host-side rejection reason (e.g. 409 Conflict /
        # 403 Forbidden) in the UI log so users see more than just "Failed".
        self._append_log(f'Connect failed: {reason}')

    # ------------------------------------------------------------------
    # Evoto launcher
    # ------------------------------------------------------------------

    def _refresh_launch_button(self) -> None:
        """Sync the Launch/Stop button label + launcher status caption."""
        if self._launcher.is_running():
            self.btn_launch.setText('Stop Evoto')
            self.launcher_status.setText('running')
        else:
            self.btn_launch.setText('Launch Evoto')
            if self._reconnect_timer.isActive():
                self.launcher_status.setText('connecting...')
            else:
                self.launcher_status.setText('not running')

    def _on_evoto_path_edited(self) -> None:
        self._config.launcher.evoto_path = self.evoto_path_edit.text().strip()
        self._schedule_save()

    def _on_pick_evoto_path(self) -> None:
        """Open a native picker for the Evoto binary or ``.app`` bundle."""
        if sys.platform == 'darwin':
            # Let the user pick either the .app bundle (typical) or the
            # Mach-O binary inside it. ``QFileDialog`` treats ``.app``
            # as a selectable file on macOS.
            start = '/Applications'
            path, _ = QFileDialog.getOpenFileName(
                self, 'Select Evoto.app or Evoto binary', start,
                'Evoto (Evoto Evoto.app)')
        elif sys.platform == 'win32':
            path, _ = QFileDialog.getOpenFileName(
                self, 'Select Evoto.exe', '',
                'Executable (*.exe)')
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, 'Select Evoto executable', '',
                'Executable (Evoto *)')
        if not path:
            return
        self.evoto_path_edit.setText(path)
        self._config.launcher.evoto_path = path
        self._schedule_save()

    def _on_auto_launch_toggled(self, checked: bool) -> None:
        self._config.launcher.auto_launch = bool(checked)
        self._schedule_save()

    def _on_toggle_launch(self) -> None:
        """Manual Launch / Stop button - always responsive.

        Stopping prefers a clean ``host.quit`` RPC when the plugin is
        connected (works for any running Evoto instance, even ones the
        demo didn't spawn). We only fall back to killing the child
        process we own if the RPC isn't available or fails.
        """
        if self._launcher.is_running() or self.connect_bar.is_connected():
            if self._request_host_quit():
                # Host will exit on the next event-loop tick; the local
                # launcher poll will notice and flip the button back.
                self._refresh_launch_button()
                return
            # RPC unavailable / failed - fall back to terminating the
            # subprocess we spawned ourselves.
            self._launcher.stop()
            self._refresh_launch_button()
            return
        path = self._config.launcher.evoto_path
        if not path:
            themed_message(
                self, 'Evoto path not set',
                'Pick the Evoto executable (or .app bundle on macOS) first.')
            return
        ok, err = self._launcher.start(path)
        if not ok:
            themed_message(self, 'Launch failed', err)
            return
        self._begin_auto_connect()
        self._refresh_launch_button()

    def _request_host_quit(self) -> bool:
        """Ask the connected host to quit via ``evoto.host.quit()``; ``True`` on success."""
        if not self.connect_bar.is_connected():
            return False
        try:
            evoto.host.quit()
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning('host.quit failed, falling back to local stop: %s', exc)
            self._append_log(f'host.quit failed: {exc}')
            return False
        self._append_log('Requested Evoto shutdown via host.quit')
        return True

    def _maybe_auto_launch(self) -> None:
        """Honour ``auto_launch`` once during startup."""
        cfg = self._config.launcher
        if not cfg.auto_launch or not cfg.evoto_path:
            return
        if self.connect_bar.is_connected():
            # Already talking to a host - nothing to do.
            return
        ok, err = self._launcher.start(cfg.evoto_path)
        if not ok:
            self._append_log(f'Auto-launch skipped: {err}')
            return
        self._begin_auto_connect()
        self._refresh_launch_button()

    def _begin_auto_connect(self, attempts: int = 30) -> None:
        """Start polling ``evoto.connect()`` until the host answers.

        Runs independently of the user's Connect button - we'll keep
        retrying until either a handshake succeeds or ``attempts``
        cycles (~60 s at the default 2 s interval) are exhausted.
        """
        if self.connect_bar.is_connected():
            return
        self._reconnect_attempts_left = attempts
        # Fire once immediately so the user sees feedback without
        # waiting a full interval; the timer handles subsequent tries.
        QTimer.singleShot(0, self._try_auto_connect)
        self._reconnect_timer.start()

    def _try_auto_connect(self) -> None:
        if self.connect_bar.is_connected():
            self._reconnect_timer.stop()
            self._reconnect_attempts_left = 0
            self._refresh_launch_button()
            return
        if self._reconnect_attempts_left <= 0:
            self._reconnect_timer.stop()
            self._append_log(
                'Auto-reconnect gave up - click Connect to try manually.')
            self._refresh_launch_button()
            return
        self._reconnect_attempts_left -= 1
        # ``try_connect`` no-ops if a worker is still handshaking, so
        # it's safe to call on every tick.
        started = self.connect_bar.try_connect()
        if started:
            self._append_log(
                f'Auto-connecting to Evoto... '
                f'({30 - self._reconnect_attempts_left}/30)')

    def _on_evoto_exited(self, rc: int) -> None:
        """Refresh UI when the child process dies on its own."""
        self._reconnect_timer.stop()
        self._refresh_launch_button()

    # ------------------------------------------------------------------
    # Project picker / creator
    # ------------------------------------------------------------------

    def _on_select_project(self):
        try:
            projects = evoto.project.list()
        except Exception as exc:
            themed_message(self, 'project.list failed', str(exc))
            return
        if not projects:
            themed_message(
                self, 'No projects',
                'The host returned no projects. Create one first.')
            return
        dlg = ProjectPickerDialog(projects, parent=self)
        if dlg.exec() != dlg.Accepted:
            return
        sel = dlg.selection()
        if not sel:
            return
        self._config.project.id = int(sel.get('id') or sel.get('project_id') or 0)
        self._config.project.name = str(sel.get('name', ''))
        self._append_log(f'Selected project #{self._config.project.id} '
                         f'"{self._config.project.name}"')
        self._schedule_save()
        self._refresh_header()

    def _on_create_project(self):
        name, ok = QInputDialog.getText(
            self, 'Create Project', 'New project name:', text='Hot Folder Project')
        if not ok or not name.strip():
            return
        try:
            result = evoto.project.create(name.strip())
        except Exception as exc:
            themed_message(self, 'project.create failed', str(exc))
            return
        pid = int(result.get('id') or result.get('project_id') or 0)
        pname = result.get('name') or name.strip()
        self._config.project.id = pid
        self._config.project.name = pname
        self._append_log(f'Created project #{pid} "{pname}"')
        self._schedule_save()
        self._refresh_header()

    # ------------------------------------------------------------------
    # Config autoload / autosave
    # ------------------------------------------------------------------

    def _auto_load(self):
        """Load the config JSON at startup if it exists; otherwise the
        demo starts empty and the first change will create the file."""
        if os.path.exists(self._config_path):
            try:
                self._config = HotFolderConfig.load(self._config_path)
                self._pipeline.set_config(self._config)
                self.table.set_watch_paths(self._config.watcher.paths)
                self.table.load_rows(self._config.mappings)
                self._append_log(f'Loaded config from {self._config_path}')
            except Exception as exc:
                self._append_log(
                    f'Failed to load {self._config_path}: {exc}. Starting empty.')
                self._config = HotFolderConfig()
        else:
            self._append_log(
                f'No config at {self._config_path} - a fresh one will be '
                f'written on the first change.')

    def _schedule_save(self):
        """Coalesce a burst of UI changes into a single debounced write."""
        if not self._autosave_enabled:
            return
        self._save_timer.start()

    def _save_now(self):
        """Flush the current UI state to disk. Errors are logged, not
        surfaced as dialogs - autosave must never interrupt the user."""
        self._pull_from_ui()
        try:
            self._config.save(self._config_path)
        except Exception as exc:
            logger.warning('autosave to %s failed: %s', self._config_path, exc)

    # ------------------------------------------------------------------
    # Mappings
    # ------------------------------------------------------------------

    def _on_add_row(self):
        self.table.add_row(MappingRow(label=f'Lane {len(self.table.rows()) + 1}'))

    def _on_rows_changed(self):
        # Keep the in-memory config in sync so Start/Stop/autosave
        # always has the latest values.
        self._config.mappings = self.table.rows()
        self._schedule_save()

    def _on_watcher_changed(self):
        self._config.watcher.include_sub_dir = self.watch_panel.include_sub_dir()
        self._config.watcher.filters = self.watch_panel.filters()
        self._schedule_save()

    def _on_watch_paths_changed(self, paths: list):
        self._config.watcher.paths = list(paths)
        self.table.set_watch_paths(self._config.watcher.paths)
        self._schedule_save()

    def _on_refresh_watch_status(self):
        """Query the host for the current watcher state and surface it."""
        try:
            watchers = evoto.watcher.list()
        except Exception as exc:
            self._append_log(f'watcher.list failed: {exc}')
            self.watch_panel.set_status_text('status: error')
            return
        if not watchers:
            self.watch_panel.set_status_text('status: no active watcher')
            self._append_log('No active watcher on host')
            return
        w = watchers[0]
        wid = str(w.get('watchId', ''))[:8]
        paths = w.get('paths') or []
        running = w.get('running', False)
        sub = w.get('includeSubDir', False)
        self.watch_panel.set_status_text(
            f'{"running" if running else "stopped"} - '
            f'{len(paths)} paths - sub={sub} - id={wid}')
        self._append_log(
            f'watcher.list: running={running}, {len(paths)} paths, '
            f'sub={sub}, id={wid}')

    def _on_row_status(self, row_id: str, text: str):
        self.table.set_status(row_id, text)

    # ------------------------------------------------------------------
    # Start / stop
    # ------------------------------------------------------------------

    def _on_toggle_run(self):
        if self._pipeline.is_running():
            self._pipeline.stop()
            self.table.set_editable(True)
            self.watch_panel.set_editable(True)
            self._refresh_header()
            self.watch_panel.set_status_text('')
        else:
            self._pull_from_ui()
            self._pipeline.set_config(self._config)
            ok, err = self._pipeline.start()
            if not ok:
                themed_message(self, 'Cannot start', err)
                return
            self.table.set_editable(False)
            self.watch_panel.set_editable(False)
            self._refresh_header()
            self._on_refresh_watch_status()

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _append_log(self, msg: str):
        ts = datetime.now().strftime('%H:%M:%S')
        self.log_view.append(f'[{ts}] {msg}')
        logger.info(msg)

    # ------------------------------------------------------------------
    # Close
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        try:
            self._pipeline.stop()
            self._reconnect_timer.stop()
            # Flush any pending autosave synchronously so the user
            # doesn't lose the latest edits on quit.
            if self._save_timer.isActive():
                self._save_timer.stop()
                self._save_now()
            # If *we* spawned Evoto, take it down with us - leaving it
            # alive would orphan a silent GUI process with no window.
            self._launcher.stop()
        finally:
            evoto.shutdown()
        event.accept()


# ---------------------------------------------------------------------------
# Small label helpers
# ---------------------------------------------------------------------------

def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty('ev_role', 'section-title')
    return lbl


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = HotFolderDemoWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
