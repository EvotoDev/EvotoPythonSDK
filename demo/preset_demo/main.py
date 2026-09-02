"""Preset API demo - prepare, apply, or reset presets on selected images.

Uses shared components for connection, project loading, preset tree, and the
image picker table.
"""

import sys
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QFrame,
    QSplitter, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal

import evoto
from demo.shared import (
    apply_theme, themed_message,
    ConnectBar, ProjectImageLoader, PresetTreeWidget, ImageTable,
)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger('preset_demo')


class PresetDemoWindow(QWidget):
    async_result_received = Signal(str, object, object)

    def __init__(self):
        super().__init__()
        self.async_result_received.connect(self._on_async_result)
        self._init_ui()
        apply_theme(self)

    # ------------------------------------------------------------------ UI --

    def _init_ui(self):
        self.setWindowTitle('Preset Demo')
        self.resize(1180, 720)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self.connect_bar = ConnectBar(title='Preset Demo')
        self.connect_bar.connected.connect(self._on_connected)
        self.connect_bar.disconnected.connect(self._on_disconnected)
        self.connect_bar.connection_failed.connect(self._on_connect_failed)
        root.addWidget(self.connect_bar)

        body = QSplitter(Qt.Horizontal)
        body.addWidget(self._build_left_panel())
        body.addWidget(self._build_image_panel())
        body.setSizes([610, 530])
        root.addWidget(body, 1)

        root.addWidget(self._build_log_panel(), 0)

    def _build_left_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.loader = ProjectImageLoader()
        self.loader.log.connect(self._log)
        self.loader.project_loaded.connect(self._on_project_loaded)
        layout.addWidget(self.loader, 0)

        self.preset_tree = PresetTreeWidget(multi_select=False)
        self.preset_tree.log.connect(self._log)
        layout.addWidget(self.preset_tree, 1)

        layout.addWidget(self._build_find_panel(), 0)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_ensure_ready = QPushButton('Ensure Ready')
        self.btn_ensure_ready.setEnabled(False)
        self.btn_ensure_ready.clicked.connect(self._on_ensure_ready)
        self.btn_apply_async = QPushButton('Apply Async')
        self.btn_apply_async.setProperty('ev_role', 'primary')
        self.btn_apply_async.setEnabled(False)
        self.btn_apply_async.clicked.connect(self._on_apply_async)
        self.btn_apply = QPushButton('Apply Preset (Sync)')
        self.btn_apply.setEnabled(False)
        self.btn_apply.clicked.connect(self._on_apply)
        self.btn_reset = QPushButton('Reset Effect')
        self.btn_reset.setEnabled(False)
        self.btn_reset.clicked.connect(self._on_reset)

        for button in (
            self.btn_ensure_ready,
            self.btn_apply_async,
            self.btn_apply,
            self.btn_reset,
        ):
            button.setMinimumWidth(0)
            button.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            button.setFixedWidth(144)

        btn_row.addStretch()
        btn_row.addWidget(self.btn_ensure_ready, 1)
        btn_row.addWidget(self.btn_apply_async, 1)
        btn_row.addWidget(self.btn_apply, 1)
        btn_row.addWidget(self.btn_reset, 1)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        return container

    def _build_find_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName('panelCard')
        frame.setFrameShape(QFrame.StyledPanel)
        inner = QVBoxLayout(frame)
        inner.setContentsMargins(12, 10, 12, 12)
        inner.setSpacing(8)

        title = QLabel('FIND PRESET ID BY NAME')
        title.setProperty('ev_role', 'section-title')
        inner.addWidget(title)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.edit_find_name = QLineEdit()
        self.edit_find_name.setPlaceholderText('Exact preset name, e.g. Soft Light')
        self.edit_find_name.setEnabled(False)
        self.edit_find_name.returnPressed.connect(self._on_find_by_name)
        row.addWidget(self.edit_find_name, 1)
        self.btn_find = QPushButton('Find ID')
        self.btn_find.setEnabled(False)
        self.btn_find.clicked.connect(self._on_find_by_name)
        row.addWidget(self.btn_find)
        inner.addLayout(row)

        self.lbl_find_result = QLabel('Matches appear here and in the events log.')
        self.lbl_find_result.setWordWrap(True)
        self.lbl_find_result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        inner.addWidget(self.lbl_find_result)

        return frame

    def _build_image_panel(self) -> QWidget:
        self.image_table = ImageTable(
            title='IMAGES',
            hint='Select one or more rows, then Apply / Reset on the left.',
        )
        self.image_table.log.connect(self._log)
        return self.image_table

    def _build_log_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName('panelCard')
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setMaximumHeight(170)
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
        self.log_view.append(msg)
        logger.info(msg)

    # --------------------------------------------------- Connection ---

    def _on_connected(self):
        self._log('Connected')
        self.loader.set_enabled(True)
        self.preset_tree.set_enabled(True)
        self.image_table.set_enabled(True)
        self.btn_ensure_ready.setEnabled(True)
        self.btn_apply_async.setEnabled(True)
        self.btn_apply.setEnabled(True)
        self.btn_reset.setEnabled(True)
        self.edit_find_name.setEnabled(True)
        self.btn_find.setEnabled(True)
        self.loader.auto_load(max_images=0)
        self.preset_tree.refresh()

    def _on_disconnected(self):
        self._log('Disconnected')
        self.loader.set_enabled(False)
        self.preset_tree.set_enabled(False)
        self.image_table.set_enabled(False)
        self.image_table.clear()
        self.btn_ensure_ready.setEnabled(False)
        self.btn_apply_async.setEnabled(False)
        self.btn_apply.setEnabled(False)
        self.btn_reset.setEnabled(False)
        self.edit_find_name.setEnabled(False)
        self.btn_find.setEnabled(False)

    def _on_connect_failed(self, reason: str):
        # Surface the real host-side rejection reason (e.g. 409 Conflict /
        # 403 Forbidden) in the UI log so users see more than just "Failed".
        self._log(f'Connect failed: {reason}')

    def _on_project_loaded(self, project_id: int, name: str):
        self.image_table.set_project(project_id, name)

    # --------------------------------------------- Preset operations ---

    def _selected_preset(self):
        ids = self.preset_tree.selected_preset_ids()
        if not ids:
            themed_message(self, 'Hint', 'Select a preset (not a category)')
            return None

        suit_id = ids[0]
        names = self.preset_tree.selected_preset_names()
        return suit_id, names[0] if names else suit_id

    def _async_callback(self, operation: str):
        def callback(result, status):
            self.async_result_received.emit(operation, result, status)

        return callback

    def _on_ensure_ready(self):
        selected = self._selected_preset()
        if selected is None:
            return
        suit_id, name = selected

        self._log(f'Ensuring "{name}" is ready (id={suit_id})')
        try:
            request_id = evoto.preset.ensure_ready_async(
                suit_ids=[suit_id],
                callback=self._async_callback('ensure_ready'),
            )
            self._log(f'Ensure-ready request queued: {request_id}')
        except Exception as exc:
            self._log(f'Failed to queue ensure-ready request: {exc}')

    def _on_apply_async(self):
        selected = self._selected_preset()
        if selected is None:
            return
        suit_id, name = selected

        image_ids = self.image_table.selected_image_ids()
        if not image_ids:
            themed_message(self, 'Hint', 'Select one or more images in the table')
            return

        self._log(
            f'Applying "{name}" asynchronously to {len(image_ids)} image(s): '
            f'{image_ids}'
        )
        try:
            request_id = evoto.preset.apply_to_image_async(
                suit_id=suit_id,
                imageIds=image_ids,
                callback=self._async_callback('apply_async'),
            )
            self._log(f'Async apply request queued: {request_id}')
        except Exception as exc:
            self._log(f'Failed to queue async apply request: {exc}')

    def _on_async_result(self, operation: str, result, status):
        if not status.is_success:
            outcome = 'timed out' if status.is_timeout else 'failed'
            self._log(
                f'{operation} {outcome}: request={status.request_id}, '
                f'code={status.error_code}, message={status.error_message}'
            )
            return

        success = result.get('success', False)
        if operation == 'ensure_ready':
            ready_ids = result.get('readySuitIds', [])
            downloaded = result.get('downloaded', False)
            self._log(
                f'Preset ready: request={status.request_id}, '
                f'success={success}, suitIds={ready_ids}, '
                f'downloaded={downloaded}'
            )
            return

        count = result.get('appliedCount', 0)
        downloaded = result.get('downloaded', False)
        self._log(
            f'Async apply completed: request={status.request_id}, '
            f'success={success}, appliedCount={count}, '
            f'downloaded={downloaded}'
        )

    def _on_apply(self):
        selected = self._selected_preset()
        if selected is None:
            return
        suit_id, name = selected

        image_ids = self.image_table.selected_image_ids()
        if not image_ids:
            themed_message(self, 'Hint', 'Select one or more images in the table')
            return

        self._log(
            f'Applying "{name}" synchronously (id={suit_id}) to '
            f'{len(image_ids)} image(s): {image_ids}'
        )
        try:
            result = evoto.preset.apply_to_image(
                suit_id=suit_id,
                imageIds=image_ids,
            )
            success = result.get('success', False)
            count = result.get('appliedCount', 0)
            self._log(f'Apply completed: success={success}, appliedCount={count}')
        except Exception as exc:
            self._log(f'Apply failed: {exc}')

    def _on_find_by_name(self):
        name = self.edit_find_name.text().strip()
        if not name:
            themed_message(self, 'Hint', 'Type a preset name to look up')
            return

        self._log(f'Looking up preset name "{name}"')
        try:
            matches = evoto.preset.find_by_name(name)
        except Exception as exc:
            # find_by_name raises ApiError 404 when no preset carries the name;
            # anything else is a real failure worth showing verbatim.
            code = getattr(exc, 'code', None)
            summary = (f'No preset named "{name}"' if code == 404
                       else f'Lookup failed: {exc}')
            self.lbl_find_result.setText(summary)
            self._log(summary)
            return

        for m in matches:
            self._log(
                f'  {m["name"]}({m["id"]}) in {m["className"]} [{m["classType"]}]'
            )
        if len(matches) == 1:
            summary = f'1 match, id = {matches[0]["id"]}'
        else:
            detail = ', '.join(f'{m["className"]} -> {m["id"]}' for m in matches)
            summary = f'{len(matches)} matches in different classes: {detail}'
        self.lbl_find_result.setText(summary)
        self._log(summary)

    def _on_reset(self):
        image_ids = self.image_table.selected_image_ids()
        if not image_ids:
            themed_message(self, 'Hint', 'Select one or more images in the table')
            return

        self._log(f'Resetting {len(image_ids)} image(s): {image_ids}')
        try:
            result = evoto.preset.reset(imageIds=image_ids)
            success = result.get('success', False)
            count = result.get('appliedCount', 0)
            self._log(f'Reset completed: success={success}, appliedCount={count}')
        except Exception as exc:
            self._log(f'Reset failed: {exc}')

    def closeEvent(self, event):
        evoto.shutdown()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = PresetDemoWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
