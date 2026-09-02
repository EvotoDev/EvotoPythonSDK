"""Plugin runtime demo - host lifecycle helpers.

This public demo focuses on connection state, ``evoto.host.quit()`` and
``evoto.host.configure_silent_timeout()``.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QPlainTextEdit, QComboBox,
    QCheckBox, QFrame, QSizePolicy, QSpinBox, QRadioButton, QButtonGroup,
)

import evoto
from evoto.core._internal.exceptions import ApiError
from demo.shared import apply_theme, themed_confirm, themed_message, ConnectBar

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger('runtime_demo')


# --------------------------------------------------------------------- workers



class _QuitWorker(QThread):
    """Run ``evoto.host.quit`` off the UI thread."""

    succeeded = Signal(dict)
    failed = Signal(str)

    def __init__(self, relaunch: bool, parent=None):
        super().__init__(parent)
        self._relaunch = bool(relaunch)

    def run(self) -> None:
        try:
            resp = evoto.host.quit(relaunch=self._relaunch) or {}
            self.succeeded.emit(resp)
        except Exception as exc:  # pylint: disable=broad-except
            self.failed.emit(str(exc))


class _SilentTimeoutWorker(QThread):
    """Run ``evoto.host.configure_silent_timeout`` off the UI thread.

    Both `timeout_seconds` and `action` are optional - ``None`` preserves
    the current host-side value. A pure-query (both None) re-reads the
    current configuration without changing anything.
    """

    succeeded = Signal(dict)
    failed = Signal(int, str)  # (error_code, message)

    def __init__(
        self,
        timeout_seconds: int | None,
        action: str | None,
        parent=None,
    ):
        super().__init__(parent)
        self._timeout_seconds = timeout_seconds
        self._action = action

    def run(self) -> None:
        try:
            resp = evoto.host.configure_silent_timeout(
                timeout_seconds=self._timeout_seconds,
                action=self._action,
            ) or {}
            self.succeeded.emit(resp)
        except ApiError as exc:
            self.failed.emit(int(exc.code), str(exc.message))
        except Exception as exc:  # pylint: disable=broad-except
            self.failed.emit(0, str(exc))


# --------------------------------------------------------------------- window


class RuntimeDemoWindow(QWidget):
    """Top-level window for host lifecycle helpers."""

    def __init__(self):
        super().__init__()
        self._quit_worker: _QuitWorker | None = None
        self._silent_worker: _SilentTimeoutWorker | None = None
        self._init_ui()
        apply_theme(self)
        self._set_controls_enabled(False)

    # ---------------------------------------------------------------- UI build

    def _init_ui(self) -> None:
        self.setWindowTitle('Plugin Runtime Demo')
        self.resize(960, 880)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self.connect_bar = ConnectBar(title='Plugin Runtime Demo')
        self.connect_bar.connected.connect(self._on_connected)
        self.connect_bar.disconnected.connect(self._on_disconnected)
        self.connect_bar.connection_failed.connect(self._on_connect_failed)
        root.addWidget(self.connect_bar)

        root.addWidget(self._build_quit_card(), 0)
        root.addWidget(self._build_silent_timeout_card(), 0)
        root.addWidget(self._build_log_panel(), 0)


    def _build_quit_card(self) -> QWidget:
        box = _Card(title='evoto.host.quit()', subtitle='Gracefully shut the host down')

        note = QLabel(
            'The host replies first, then exits on the next event-loop tick. '
            'The IPC channel drops immediately afterwards, so the plugin '
            'typically auto-disconnects within a second.'
        )
        note.setWordWrap(True)
        note.setProperty('ev_role', 'section-caption')
        box.layout().addWidget(note)

        self.relaunch_cb = QCheckBox('Relaunch after quit')
        box.layout().addWidget(self.relaunch_cb)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.quit_btn = QPushButton('Quit Host')
        self.quit_btn.setProperty('ev_role', 'danger')
        self.quit_btn.clicked.connect(self._on_quit_clicked)
        btn_row.addWidget(self.quit_btn)
        box.layout().addLayout(btn_row)
        return box

    def _build_silent_timeout_card(self) -> QWidget:
        """UI for ``evoto.host.configure_silent_timeout()``.

        Lets the user dial in a timeout (seconds or minutes) and pick
        the action - ``quit`` kills the host, ``show`` flips it out of
        silent mode and shows the main window. The card is only useful
        when the host was launched with ``-silent``; otherwise applying
        returns 412 and we surface that as a one-line warning.
        """
        box = _Card(
            title='evoto.host.configure_silent_timeout()',
            subtitle='Silent-mode auto-exit watcher',
        )

        note = QLabel(
            'Only effective when the host is launched with <code>-silent</code>. '
            'Timer pauses while any plugin is connected and resumes when the '
            'last plugin disconnects. Timeout <= 0 disables auto-exit.'
        )
        note.setWordWrap(True)
        note.setTextFormat(Qt.RichText)
        note.setProperty('ev_role', 'section-caption')
        box.layout().addWidget(note)

        # Current state readout - filled in after Apply / Refresh.
        self.silent_state = QLabel('Current: (not queried yet)')
        self.silent_state.setProperty('ev_role', 'section-caption')
        self.silent_state.setWordWrap(True)
        box.layout().addWidget(self.silent_state)

        # Row 1: timeout value + unit.
        row_timeout = QHBoxLayout()
        row_timeout.setSpacing(8)
        row_timeout.addWidget(_FieldLabel('Timeout'))

        self.silent_value = QSpinBox()
        # Up to 24 h in seconds covers anything a demo ever needs to test.
        self.silent_value.setRange(0, 24 * 60 * 60)
        self.silent_value.setValue(5)
        self.silent_value.setSuffix('')
        self.silent_value.setMinimumWidth(100)
        row_timeout.addWidget(self.silent_value)

        self.silent_unit = QComboBox()
        self.silent_unit.addItems(['minutes', 'seconds'])
        self.silent_unit.setCurrentIndex(0)
        self.silent_unit.setMinimumWidth(100)
        row_timeout.addWidget(self.silent_unit)

        row_timeout.addStretch(1)
        box.layout().addLayout(row_timeout)

        # Row 2: action radio.
        row_action = QHBoxLayout()
        row_action.setSpacing(12)
        row_action.addWidget(_FieldLabel('Action'))

        self.silent_action_group = QButtonGroup(self)
        self.silent_action_quit = QRadioButton('quit (close host)')
        self.silent_action_quit.setChecked(True)
        self.silent_action_show = QRadioButton('show (exit silent + show main window)')
        self.silent_action_group.addButton(self.silent_action_quit)
        self.silent_action_group.addButton(self.silent_action_show)
        row_action.addWidget(self.silent_action_quit)
        row_action.addWidget(self.silent_action_show)
        row_action.addStretch(1)
        box.layout().addLayout(row_action)

        # Row 3: buttons.
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.silent_refresh_btn = QPushButton('Refresh')
        self.silent_refresh_btn.setProperty('ev_role', 'ghost')
        self.silent_refresh_btn.clicked.connect(self._on_silent_refresh_clicked)
        btn_row.addWidget(self.silent_refresh_btn)

        self.silent_apply_btn = QPushButton('Apply')
        self.silent_apply_btn.setProperty('ev_role', 'primary')
        self.silent_apply_btn.clicked.connect(self._on_silent_apply_clicked)
        btn_row.addWidget(self.silent_apply_btn)

        box.layout().addLayout(btn_row)
        return box

    def _build_log_panel(self) -> QWidget:
        box = _Card(title='Log', subtitle='Runtime events')
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(2000)
        self.log_view.setMinimumHeight(120)
        box.layout().addWidget(self.log_view, 1)
        return box

    # ---------------------------------------------------------------- helpers

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.quit_btn.setEnabled(enabled)
        # Silent-timeout card is only meaningful while connected - the RPC
        # wouldn't even reach the host otherwise.
        self.silent_value.setEnabled(enabled)
        self.silent_unit.setEnabled(enabled)
        self.silent_action_quit.setEnabled(enabled)
        self.silent_action_show.setEnabled(enabled)
        self.silent_refresh_btn.setEnabled(enabled and self._silent_worker is None)
        self.silent_apply_btn.setEnabled(enabled and self._silent_worker is None)
        if not enabled:
            self.silent_state.setText('Current: (disconnected)')

    def _log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    # ---------------------------------------------------------------- slots

    def _on_connected(self) -> None:
        self._set_controls_enabled(True)
        self._log('Connected to host.')
        # Snapshot the current silent-mode config so the readout is
        # filled in before the user touches anything.
        self._run_silent_query()

    def _on_disconnected(self) -> None:
        self._set_controls_enabled(False)
        self._log('Disconnected.')

    def _on_connect_failed(self, reason: str) -> None:
        # Surface the real host-side rejection reason (e.g. 409 Conflict /
        # 403 Forbidden) in the UI log so users see more than just the
        # "Failed" status badge.
        self._log(f'Connect failed: {reason}')


    def _on_quit_clicked(self) -> None:
        if self._quit_worker is not None:
            return
        relaunch = self.relaunch_cb.isChecked()
        if not themed_confirm(
            self,
            'Quit Host',
            'Shut the Evoto host down now?',
            informative=f'Relaunch after quit: {relaunch}',
        ):
            return
        self.quit_btn.setEnabled(False)
        self.quit_btn.setText('Quitting...')
        self._log(f'evoto.host.quit(relaunch={relaunch})')
        worker = _QuitWorker(relaunch, self)
        worker.succeeded.connect(self._on_quit_success)
        worker.failed.connect(self._on_quit_failed)
        worker.finished.connect(self._on_quit_finished)
        self._quit_worker = worker
        worker.start()

    def _on_quit_success(self, resp: dict) -> None:
        self._log(f'  -> {resp}')

    def _on_quit_failed(self, msg: str) -> None:
        self._log(f'  ✗ quit failed: {msg}')
        themed_message(self, 'quit_host failed', msg)

    def _on_quit_finished(self) -> None:
        self.quit_btn.setText('Quit Host')
        self.quit_btn.setEnabled(self.connect_bar.is_connected())
        self._quit_worker = None

    # -------------------------------------------------- silent timeout slots

    def _timeout_seconds_from_inputs(self) -> int:
        """Translate the spinbox + unit into a single ``timeout_seconds`` int.

        ``minutes`` unit multiplies by 60. A value of 0 is preserved as-is
        (the host reads that as "disable auto-exit").
        """
        value = self.silent_value.value()
        if self.silent_unit.currentText() == 'minutes':
            value *= 60
        return value

    def _selected_action(self) -> str:
        return 'show' if self.silent_action_show.isChecked() else 'quit'

    def _run_silent_query(self) -> None:
        """Query current config without changing anything (both params None)."""
        if self._silent_worker is not None:
            return
        self._dispatch_silent_worker(timeout_seconds=None, action=None, label='query')

    def _on_silent_refresh_clicked(self) -> None:
        self._run_silent_query()

    def _on_silent_apply_clicked(self) -> None:
        if self._silent_worker is not None:
            return
        seconds = self._timeout_seconds_from_inputs()
        action = self._selected_action()
        self._dispatch_silent_worker(
            timeout_seconds=seconds,
            action=action,
            label=f'apply timeout={seconds}s action={action}',
        )

    def _dispatch_silent_worker(
        self,
        *,
        timeout_seconds: int | None,
        action: str | None,
        label: str,
    ) -> None:
        self.silent_apply_btn.setEnabled(False)
        self.silent_refresh_btn.setEnabled(False)
        self._log(f'evoto.host.configure_silent_timeout()  # {label}')
        worker = _SilentTimeoutWorker(timeout_seconds, action, self)
        worker.succeeded.connect(self._on_silent_success)
        worker.failed.connect(self._on_silent_failed)
        worker.finished.connect(self._on_silent_finished)
        self._silent_worker = worker
        worker.start()

    def _on_silent_success(self, resp: dict) -> None:
        self._log(f'  -> {resp}')
        timeout_s = resp.get('timeout_seconds', '?')
        action = resp.get('action', '?')
        enabled = resp.get('enabled', False)
        plugins = resp.get('connected_plugin_count', 0)
        try:
            minutes_hint = f' ({timeout_s / 60:.1f} min)' if isinstance(timeout_s, int) else ''
        except Exception:
            minutes_hint = ''
        status = 'auto-exit enabled' if enabled else 'auto-exit DISABLED'
        self.silent_state.setText(
            f'Current: timeout={timeout_s}s{minutes_hint}, action={action}, '
            f'{status}, connected_plugins={plugins}'
        )

    def _on_silent_failed(self, code: int, msg: str) -> None:
        if code == 412:
            # Host is not running in silent mode - this is expected; surface it
            # without the scary red message box.
            self._log(f'  ✗ silentTimeout rejected (412): {msg}')
            self.silent_state.setText(
                'Current: host is NOT in silent mode '
                '(launch the host with -silent to use this feature)'
            )
        else:
            self._log(f'  ✗ silentTimeout failed [{code}]: {msg}')
            themed_message(self, 'configure_silent_timeout failed', msg)

    def _on_silent_finished(self) -> None:
        self._silent_worker = None
        connected = self.connect_bar.is_connected()
        self.silent_apply_btn.setEnabled(connected)
        self.silent_refresh_btn.setEnabled(connected)


# ----------------------------------------------------------------- small UI


class _Card(QFrame):
    """Titled card container matching the other demos."""

    def __init__(self, title: str, subtitle: str = ''):
        super().__init__()
        self.setObjectName('panelCard')
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)
        title_lbl = QLabel(title)
        title_lbl.setProperty('ev_role', 'section-title')
        header.addWidget(title_lbl)
        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setProperty('ev_role', 'section-caption')
            header.addWidget(sub_lbl, 1)
        else:
            header.addStretch(1)
        outer.addLayout(header)

        self._body = QVBoxLayout()
        self._body.setContentsMargins(0, 0, 0, 0)
        self._body.setSpacing(8)
        outer.addLayout(self._body, 1)

    def layout(self) -> QVBoxLayout:  # type: ignore[override]
        return self._body


class _FieldLabel(QLabel):
    def __init__(self, text: str):
        super().__init__(text)
        self.setProperty('ev_role', 'field-label')


# ------------------------------------------------------------------ entry

def main() -> int:
    app = QApplication(sys.argv)
    window = RuntimeDemoWindow()
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
