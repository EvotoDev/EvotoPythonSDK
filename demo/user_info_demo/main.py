"""User-info demo - ``evoto.user.info()``.

Fetches the currently signed-in user (display name, email, credit balance,
cloud storage usage, subscription / VIP flags) via the one-shot
``user.info`` RPC and renders them in a small dashboard. There is no event
channel for user info, so this demo also shows the typical polling loop you
would run if you want to track credits dropping in real time.

The actual SDK surface is tiny: everything this window does goes through
``evoto.user.info()`` and the :class:`evoto.UserInfo` dataclass it returns.
Use this as the "hello world" template for any plugin that needs to show
the signed-in account.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton, QSizePolicy, QSpinBox,
    QVBoxLayout, QWidget,
)

import evoto
from evoto import UserInfo
from demo.shared import ConnectBar, apply_theme, themed_message

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger('user_info_demo')


# --------------------------------------------------------------------- worker


class _UserInfoWorker(QThread):
    """Run ``evoto.user.info()`` off the UI thread.

    The RPC is fast but we still marshal it onto a background thread so the
    polling loop (or a slow host) cannot stall the Qt event loop.
    """

    succeeded = Signal(object)  # UserInfo
    failed = Signal(str)

    def run(self) -> None:
        try:
            me = evoto.user.info()
            self.succeeded.emit(me)
        except Exception as exc:  # pylint: disable=broad-except
            self.failed.emit(str(exc))


# --------------------------------------------------------------------- window


class UserInfoDemoWindow(QWidget):
    """Top-level window: fetch / poll / display user info."""

    def __init__(self):
        super().__init__()
        self._worker: _UserInfoWorker | None = None
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._on_fetch_clicked)
        self._last_snapshot: UserInfo | None = None
        self._init_ui()
        apply_theme(self)
        self._set_controls_enabled(False)

    # ---------------------------------------------------------------- UI build

    def _init_ui(self) -> None:
        self.setWindowTitle('User Info Demo')
        self.resize(820, 720)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self.connect_bar = ConnectBar(title='User Info Demo')
        self.connect_bar.connected.connect(self._on_connected)
        self.connect_bar.disconnected.connect(self._on_disconnected)
        self.connect_bar.connection_failed.connect(self._on_connect_failed)
        root.addWidget(self.connect_bar)

        root.addWidget(self._build_actions_card(), 0)
        root.addWidget(self._build_profile_card(), 0)
        root.addWidget(self._build_credits_card(), 0)
        root.addWidget(self._build_cloud_card(), 0)
        root.addWidget(self._build_log_panel(), 1)

    def _build_actions_card(self) -> QWidget:
        box = _Card(title='evoto.user.info()', subtitle='One-shot RPC - no event channel')

        row = QHBoxLayout()
        row.setSpacing(8)

        self.fetch_btn = QPushButton('Fetch Now')
        self.fetch_btn.setProperty('ev_role', 'primary')
        self.fetch_btn.clicked.connect(self._on_fetch_clicked)
        row.addWidget(self.fetch_btn)

        self.auto_cb = QCheckBox('Auto-refresh every')
        self.auto_cb.toggled.connect(self._on_auto_toggled)
        row.addWidget(self.auto_cb)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(2, 300)
        self.interval_spin.setValue(10)
        self.interval_spin.setSuffix(' s')
        self.interval_spin.valueChanged.connect(self._on_interval_changed)
        row.addWidget(self.interval_spin)

        row.addStretch(1)
        box.layout().addLayout(row)
        return box

    def _build_profile_card(self) -> QWidget:
        box = _Card(title='Profile', subtitle='From ShareObjectModel::UserModel')

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(6)

        self.lbl_user_id = _ValueLabel('-')
        self.lbl_display_name = _ValueLabel('-')
        self.lbl_email = _ValueLabel('-')
        self.lbl_flags = _ValueLabel('-')

        for row, (key, value) in enumerate([
            ('User ID',       self.lbl_user_id),
            ('Display name',  self.lbl_display_name),
            ('Email',         self.lbl_email),
            ('Flags',         self.lbl_flags),
        ]):
            grid.addWidget(_FieldLabel(key), row, 0)
            grid.addWidget(value, row, 1)

        grid.setColumnStretch(1, 1)
        box.layout().addLayout(grid)
        return box

    def _build_credits_card(self) -> QWidget:
        box = _Card(title='Credits', subtitle='Mirrors the in-app account popover')

        row = QHBoxLayout()
        row.setSpacing(24)
        self.lbl_credits_remaining = _ValueLabel('-')
        self.lbl_credits_used = _ValueLabel('-')
        self.lbl_credits_total = _ValueLabel('-')
        for key, value in [
            ('Remaining', self.lbl_credits_remaining),
            ('Used',      self.lbl_credits_used),
            ('Total',     self.lbl_credits_total),
        ]:
            col = QVBoxLayout()
            col.setSpacing(2)
            col.addWidget(_FieldLabel(key))
            col.addWidget(value)
            row.addLayout(col)
        row.addStretch(1)
        box.layout().addLayout(row)

        # Show usage as plain text rather than a blue bar so it blends
        # into the dark theme.
        self.lbl_credits_usage = QLabel('-')
        self.lbl_credits_usage.setProperty('ev_role', 'section-caption')
        box.layout().addWidget(self.lbl_credits_usage)
        return box

    def _build_cloud_card(self) -> QWidget:
        box = _Card(title='Cloud Storage & Subscription', subtitle='From AppContext')

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(6)

        self.lbl_cloud = _ValueLabel('-')
        self.lbl_next_bill = _ValueLabel('-')

        for row, (key, value) in enumerate([
            ('Cloud usage',     self.lbl_cloud),
            ('Next bill date',  self.lbl_next_bill),
        ]):
            grid.addWidget(_FieldLabel(key), row, 0)
            grid.addWidget(value, row, 1)

        grid.setColumnStretch(1, 1)
        box.layout().addLayout(grid)
        return box

    def _build_log_panel(self) -> QWidget:
        box = _Card(title='Log', subtitle='RPC calls & errors')
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(2000)
        self.log_view.setMinimumHeight(120)
        box.layout().addWidget(self.log_view, 1)
        return box

    # ---------------------------------------------------------------- helpers

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.fetch_btn.setEnabled(enabled)
        self.auto_cb.setEnabled(enabled)
        self.interval_spin.setEnabled(enabled and self.auto_cb.isChecked())
        if not enabled and self._poll_timer.isActive():
            self._poll_timer.stop()

    def _log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def _render_snapshot(self, me: UserInfo) -> None:
        self._last_snapshot = me

        self.lbl_user_id.setText(str(me.user_id) if me.user_id >= 0 else '-')
        self.lbl_display_name.setText(me.display_name or '-')
        self.lbl_email.setText(me.email or '-')

        flags = []
        if me.is_subscribed:
            flags.append('Subscribed')
        if me.is_vip:
            flags.append('VIP')
        self.lbl_flags.setText(', '.join(flags) if flags else 'Free')

        self.lbl_credits_remaining.setText(_fmt_credits(me.credits_remaining))
        self.lbl_credits_used.setText(_fmt_credits(me.credits_used))
        self.lbl_credits_total.setText(_fmt_credits(me.credits_total))

        # Percentage text; clamp to 0..100 in case the host returns
        # something out of range.
        if me.credits_total > 0:
            pct = max(0, min(100, round(me.credits_remaining / me.credits_total * 100)))
            self.lbl_credits_usage.setText(
                f'{_fmt_credits(me.credits_remaining)} of '
                f'{_fmt_credits(me.credits_total)} remaining - {pct}%'
            )
        else:
            self.lbl_credits_usage.setText('no active plan')

        if me.has_cloud_space:
            self.lbl_cloud.setText(f'{me.cloud_used_space} / {me.cloud_total_space}')
        else:
            self.lbl_cloud.setText('no cloud entitlement')

        self.lbl_next_bill.setText(me.next_bill_date or '- (no active subscription)')

    # ---------------------------------------------------------------- slots

    def _on_connected(self) -> None:
        self._set_controls_enabled(True)
        self._log('Connected to host.')
        self._on_fetch_clicked()

    def _on_disconnected(self) -> None:
        self._set_controls_enabled(False)
        self.auto_cb.setChecked(False)
        self._log('Disconnected.')

    def _on_connect_failed(self, reason: str) -> None:
        # Surface the real host-side rejection reason (e.g. 409 Conflict /
        # 403 Forbidden) in the UI log so users see more than just "Failed".
        self._log(f'Connect failed: {reason}')

    def _on_fetch_clicked(self) -> None:
        if self._worker is not None:
            return
        self.fetch_btn.setEnabled(False)
        self._log('evoto.user.info()')
        worker = _UserInfoWorker(self)
        worker.succeeded.connect(self._on_info_success)
        worker.failed.connect(self._on_info_failed)
        worker.finished.connect(self._on_info_finished)
        self._worker = worker
        worker.start()

    def _on_info_success(self, me: UserInfo) -> None:
        self._render_snapshot(me)
        self._log(
            f'  -> {me.display_name or "(no name)"} - '
            f'credits {me.credits_remaining:g}/{me.credits_total:g} - '
            f'cloud={"yes" if me.has_cloud_space else "no"}'
        )

    def _on_info_failed(self, msg: str) -> None:
        self._log(f'  ✗ user.info failed: {msg}')
        themed_message(self, 'user.info failed', msg)

    def _on_info_finished(self) -> None:
        self.fetch_btn.setEnabled(self.connect_bar.is_connected())
        self._worker = None

    def _on_auto_toggled(self, checked: bool) -> None:
        self.interval_spin.setEnabled(checked and self.connect_bar.is_connected())
        if checked:
            self._poll_timer.start(self.interval_spin.value() * 1000)
            self._log(f'Polling every {self.interval_spin.value()}s.')
        else:
            self._poll_timer.stop()
            self._log('Polling stopped.')

    def _on_interval_changed(self, value: int) -> None:
        if self._poll_timer.isActive():
            self._poll_timer.start(value * 1000)


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


class _ValueLabel(QLabel):
    """Prominent value readout aligned next to a field label."""

    def __init__(self, text: str):
        super().__init__(text)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setStyleSheet('color: #f3f0e8; font-weight: 600;')


def _fmt_credits(value: float) -> str:
    """Format a credit count: integer when it looks like one, else 2dp."""
    if abs(value - round(value)) < 1e-6:
        return f'{int(round(value))}'
    return f'{value:.2f}'


# ------------------------------------------------------------------ entry

def main() -> int:
    app = QApplication(sys.argv)
    window = UserInfoDemoWindow()
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
