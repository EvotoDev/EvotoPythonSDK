"""Shared widgets for the phase-2 API demos."""

from __future__ import annotations

import json
from typing import Any, Callable

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import evoto
from demo.shared import (
    ConnectBar,
    ImageTable,
    ProjectImageLoader,
    themed_message,
    themed_notify,
)


class CallWorker(QThread):
    """Run one SDK call off the Qt UI thread."""

    succeeded = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self, label: str, fn: Callable[[], object], parent=None):
        super().__init__(parent)
        self._label = label
        self._fn = fn

    def run(self) -> None:
        try:
            self.succeeded.emit(self._label, self._fn())
        except Exception as exc:  # pylint: disable=broad-except
            self.failed.emit(self._label, str(exc))


class Phase2DemoWindow(QWidget):
    """Common shell for one API-domain demo."""

    window_title = "Phase 2 Demo"
    connect_title = "Phase 2 Demo"
    image_hint = "Select rows before running operations."
    auto_load_count = 20

    def __init__(self):
        super().__init__()
        self._worker: CallWorker | None = None
        self._init_ui()
        self._set_connected_controls(False)

    def _init_ui(self) -> None:
        self.setWindowTitle(self.window_title)
        self.resize(1180, 780)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self.connect_bar = ConnectBar(title=self.connect_title)
        self.connect_bar.connected.connect(self._on_connected)
        self.connect_bar.disconnected.connect(self._on_disconnected)
        self.connect_bar.connection_failed.connect(self._on_connect_failed)
        root.addWidget(self.connect_bar)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([500, 680])
        root.addWidget(splitter, 1)

    def _build_left_panel(self) -> QWidget:
        left = QWidget()
        layout = QVBoxLayout(left)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.loader = ProjectImageLoader(title="PROJECT SOURCE")
        self.loader.log.connect(self._log)
        self.loader.project_loaded.connect(self._on_project_loaded)
        self.loader.images_loaded.connect(self._on_images_loaded)
        layout.addWidget(self.loader, 0)

        self.image_table = ImageTable(
            title="CURRENT PROJECT IMAGES",
            hint=self.image_hint,
        )
        self.image_table.log.connect(self._log)
        layout.addWidget(self.image_table, 1)
        return left

    def _build_right_panel(self) -> QWidget:
        right = QWidget()
        layout = QVBoxLayout(right)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self.build_actions_panel(), 0)
        layout.addWidget(self._build_log_panel(), 1)
        return right

    def build_actions_panel(self) -> QWidget:
        raise NotImplementedError

    def _build_log_panel(self) -> QWidget:
        box = Card(title="Result Log", subtitle="RPC responses")
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(3000)

        toolbar = QHBoxLayout()
        toolbar.addStretch(1)
        clear_btn = QPushButton("Clear Log")
        clear_btn.setProperty("ev_role", "ghost")
        clear_btn.clicked.connect(self.log_view.clear)
        toolbar.addWidget(clear_btn)
        box.layout().addLayout(toolbar)

        box.layout().addWidget(self.log_view, 1)
        return box

    def action_button(self, text: str, handler: Callable[[], None]) -> QPushButton:
        btn = QPushButton(text)
        btn.clicked.connect(handler)
        return btn

    def _set_connected_controls(self, enabled: bool) -> None:
        self.loader.set_enabled(enabled)
        self.image_table.set_enabled(enabled)
        for btn in self.findChildren(QPushButton):
            if btn is self.connect_bar.btn:
                continue
            btn.setEnabled(enabled)

    def _log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def _project_id(self) -> int:
        project_id = self.loader.project_id
        if not project_id:
            raise RuntimeError("Load the current project first.")
        return int(project_id)

    def _selected_ids(self, *, minimum: int = 1) -> list[int]:
        image_ids = self.image_table.selected_image_ids()
        if not image_ids:
            image_ids = self.loader.image_ids
        if len(image_ids) < minimum:
            raise RuntimeError(
                f"Select at least {minimum} image(s), or load more images."
            )
        return image_ids

    def _run(self, label: str, fn: Callable[[], object]) -> None:
        if self._worker is not None:
            themed_message(self, "Busy", "Wait for the current request to finish.")
            return
        self._set_request_enabled(False)
        self._log(f"> {label}")
        worker = CallWorker(label, fn, self)
        worker.succeeded.connect(self._on_call_success)
        worker.failed.connect(self._on_call_failed)
        worker.finished.connect(self._on_call_finished)
        self._worker = worker
        worker.start()

    def _set_request_enabled(self, enabled: bool) -> None:
        if not self.connect_bar.is_connected():
            enabled = False
        for btn in self.findChildren(QPushButton):
            if btn is self.connect_bar.btn:
                continue
            btn.setEnabled(enabled)

    @staticmethod
    def _pretty(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)

    @staticmethod
    def _combo(items: list[tuple[str, Any]], *, default_value: Any) -> QComboBox:
        combo = QComboBox()
        for label, value in items:
            combo.addItem(label, value)
        index = combo.findData(default_value)
        if index >= 0:
            combo.setCurrentIndex(index)
        return combo

    @staticmethod
    def _combo_value(combo: QComboBox) -> Any:
        return combo.currentData()

    def _on_connected(self) -> None:
        self._set_connected_controls(True)
        self._log("Connected.")
        self.loader.auto_load(max_images=self.auto_load_count)

    def _on_disconnected(self) -> None:
        self._set_connected_controls(False)
        self.image_table.clear()
        self._log("Disconnected.")

    def _on_connect_failed(self, reason: str) -> None:
        self._log(f"Connect failed: {reason}")

    def _on_project_loaded(self, project_id: int, name: str) -> None:
        self.image_table.set_project(project_id, name)

    def _on_images_loaded(self, image_ids: list[int]) -> None:
        if image_ids:
            self._log(f"Workflow image IDs ready: {image_ids[:10]}")

    def _on_call_success(self, label: str, payload: object) -> None:
        self._log(f"< {label}\n{self._pretty(payload)}")

    def _on_call_failed(self, label: str, message: str) -> None:
        # Non-modal: a request failure / timeout fires from a background
        # worker, possibly after the app has lost foreground focus. A
        # blocking modal popup could trap the main thread with an
        # unclickable window (see ``themed_notify``); the failure is also
        # always recorded in the result log above.
        self._log(f"< {label} failed: {message}")
        themed_notify(self, f"{label} failed", message)

    def _on_call_finished(self) -> None:
        self._worker = None
        self._set_request_enabled(True)

    def closeEvent(self, event) -> None:
        evoto.shutdown()
        event.accept()


class Card(QFrame):
    """Titled card container matching the other demos."""

    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        self.setObjectName("panelCard")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)
        title_lbl = QLabel(title)
        title_lbl.setProperty("ev_role", "section-title")
        header.addWidget(title_lbl)
        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setProperty("ev_role", "section-caption")
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


class FieldLabel(QLabel):
    """Small muted form label."""

    def __init__(self, text: str):
        super().__init__(text)
        self.setProperty("ev_role", "field-label")
