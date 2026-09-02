"""Reusable connection banner widget."""

import logging

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton

import evoto

from .env_config import load_env_info, resolve_socket_path

logger = logging.getLogger(__name__)


class _ConnectWorker(QThread):
    succeeded = Signal()
    failed = Signal(str)

    def __init__(self, socket_path: str, parent=None):
        super().__init__(parent)
        self._socket_path = socket_path

    def run(self):
        try:
            evoto.connect(self._socket_path)
            self.succeeded.emit()
        except Exception as exc:
            self.failed.emit(str(exc))


class ConnectBar(QWidget):
    """Banner bar with status label + Connect/Disconnect button.

    Signals:
        connected: emitted after successful handshake.
        disconnected: emitted when the bar leaves the "Connected" state -
            either because the user clicked Disconnect *or* the host went
            away (crash, ``evoto.host.quit``, process kill). Handlers can
            therefore treat it as a generic "link lost" hook.
    """

    connected = Signal()
    disconnected = Signal()
    #: Emitted when ``evoto.connect()`` raises. Carries the exception's
    #: string form so demos can surface the host-side rejection reason
    #: (e.g. 409 Conflict, 403 Forbidden) in their own UI / Log pane.
    connection_failed = Signal(str)

    # Internal signal used to marshal the host-shutdown callback (which fires
    # on the SDK receiver thread) back onto the Qt GUI thread.
    _host_lost_internal = Signal()

    def __init__(self, title: str = '', parent=None):
        super().__init__(parent)
        self._worker: _ConnectWorker | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        if title:
            lbl = QLabel(title)
            lbl.setStyleSheet('font-weight: bold; font-size: 14px; color: #f3f0e8;')
            layout.addWidget(lbl)

        layout.addStretch()

        # Environment badge - only visible when a non-production env
        # has been configured, so production demos keep a clean banner.
        self._env_info = load_env_info()
        self.env_label = QLabel()
        self._refresh_env_badge()
        layout.addWidget(self.env_label)

        self.status_label = QLabel('Disconnected')
        self._set_state('disconnected')
        layout.addWidget(self.status_label)

        self.btn = QPushButton('Connect')
        self.btn.clicked.connect(self._on_click)
        layout.addWidget(self.btn)

        self._host_lost_internal.connect(self._on_host_lost)
        # Persistent hook: the runtime keeps its shutdown callbacks across
        # reconnects, so a single registration covers every future session.
        evoto.on_shutdown(self._notify_host_lost)

    def _notify_host_lost(self) -> None:
        """Called from the SDK receiver thread when the host goes away.

        We just hop back onto the GUI thread via ``_host_lost_internal``;
        the actual UI flip happens in :meth:`_on_host_lost`.
        """
        try:
            self._host_lost_internal.emit()
        except RuntimeError:
            # Widget was deleted before we got here; nothing to update.
            logger.debug("ConnectBar already destroyed; ignoring host-lost event")

    def _set_state(self, state: str):
        self.status_label.setProperty('ev_role', f'status-{state}')
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _refresh_env_badge(self) -> None:
        """Show a tag like ``[dev]`` when a non-prod env is configured.

        Hidden entirely in the default ``pro`` case so production demos
        don't grow UI chrome they don't need.
        """
        env = self._env_info.get('env')
        source = self._env_info.get('source')
        socket_path = self._env_info.get('socket_path', '')

        if source == 'env_var':
            text = '[custom]'
            tip = f'Custom endpoint: {socket_path}'
        elif env and env != 'pro':
            text = f'[{env}]'
            tip = f'Endpoint: {socket_path}'
        else:
            self.env_label.hide()
            return

        self.env_label.setText(text)
        self.env_label.setToolTip(tip)
        self.env_label.setProperty('ev_role', 'env-badge-nonprod')
        self.env_label.style().unpolish(self.env_label)
        self.env_label.style().polish(self.env_label)
        self.env_label.show()

    def is_connected(self) -> bool:
        """True when the SDK reports a live host connection.

        Note this reads the real runtime state instead of the label text, so
        it stays honest even if the host disappeared before the UI had a
        chance to repaint.
        """
        return bool(evoto.host.is_connected)

    def is_connecting(self) -> bool:
        """True while the background handshake worker is still running."""
        return self._worker is not None and self._worker.isRunning()

    def try_connect(self) -> bool:
        """Kick off a connect attempt if we're currently idle.

        Returns ``True`` when a fresh worker was started, ``False`` if
        the bar is already connected or a previous attempt is still in
        flight. Host code uses this to poll ``evoto.connect()`` from
        an auto-launch / retry loop without touching button internals.
        """
        if self.is_connected() or self.is_connecting():
            return False
        self._do_connect()
        return True

    def _on_click(self):
        if self.is_connected():
            self._do_disconnect()
        else:
            self._do_connect()

    def _do_connect(self):
        self.btn.setEnabled(False)
        self.status_label.setText('Connecting...')
        self._set_state('connecting')
        socket_path = resolve_socket_path()
        logger.info('ConnectBar: connecting to %s', socket_path)
        self._worker = _ConnectWorker(socket_path)
        self._worker.succeeded.connect(self._on_connected)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_connected(self):
        self.status_label.setText('Connected')
        self._set_state('connected')
        self.btn.setEnabled(True)
        self.btn.setText('Disconnect')
        self.connected.emit()

    def _on_failed(self, err: str):
        # ``err`` carries the full host rejection reason (e.g.
        # "Host rejected handshake [409]: plugin_id ... is already bound to
        # another connection"). We both log it and re-emit via
        # ``connection_failed`` so each demo can show it in its own log pane.
        logger.warning('ConnectBar: connect failed: %s', err)
        self.status_label.setText('Failed')
        self._set_state('disconnected')
        self.btn.setEnabled(True)
        self.btn.setText('Connect')
        self.connection_failed.emit(err)

    def _do_disconnect(self):
        evoto.disconnect()
        self._apply_disconnected_ui()
        self.disconnected.emit()

    def _on_host_lost(self):
        """Runs on the GUI thread whenever the host side drops.

        Ignored when the bar is mid-handshake or already visibly
        disconnected, so involuntary drops don't race with the normal
        connect/disconnect flow.
        """
        if self.status_label.text() == 'Disconnected':
            return
        if self.is_connecting():
            return
        logger.info('ConnectBar: host connection lost, flipping UI back')
        self._apply_disconnected_ui()
        self.disconnected.emit()

    def _apply_disconnected_ui(self):
        self.status_label.setText('Disconnected')
        self._set_state('disconnected')
        self.btn.setEnabled(True)
        self.btn.setText('Connect')
