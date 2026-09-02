"""Metadata automation demo."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import evoto
from demo.shared import (
    Card,
    FieldLabel,
    Phase2DemoWindow,
    apply_theme,
)
from evoto.core.api_fields import (
    MetadataColorLabel,
    MetadataField,
    MetadataFlag,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("metadata_demo")


class MetadataDemoWindow(Phase2DemoWindow):
    """Dedicated MetadataAPI debug window."""

    file_event_received = Signal(str, object)

    window_title = "Metadata Automation Demo"
    connect_title = "Metadata Automation Demo"
    image_hint = "Select rows before reading or writing metadata."

    def __init__(self):
        self._file_event_callbacks: list[tuple[str, object]] = []
        super().__init__()
        self.file_event_received.connect(self._on_file_event_main)

    def build_actions_panel(self) -> QWidget:
        box = Card(
            title="MetadataAPI",
            subtitle="Read/write metadata, refresh from file, save to sidecar",
        )

        form = QGridLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(8)

        self.metadata_title = QLineEdit("Client selects")
        self.metadata_caption = QLineEdit("Metadata demo caption")
        self.metadata_creator = QLineEdit("Automation Demo")
        self.metadata_copyright = QLineEdit("Copyright 2026")
        self.metadata_supplemental_categories = QLineEdit("client-a,wedding,selected")
        self.metadata_rating = self._combo([
            ("No rating", 0),
            ("1 star", 1),
            ("2 stars", 2),
            ("3 stars", 3),
            ("4 stars", 4),
            ("5 stars", 5),
        ], default_value=5)
        self.metadata_color_label = self._combo([
            ("None", MetadataColorLabel.NONE),
            ("Green", MetadataColorLabel.GREEN),
            ("Purple", MetadataColorLabel.PURPLE),
            ("Blue", MetadataColorLabel.BLUE),
            ("Yellow", MetadataColorLabel.YELLOW),
            ("Red", MetadataColorLabel.RED),
        ], default_value=MetadataColorLabel.NONE)
        self.metadata_flag = self._combo([
            ("Unflagged", MetadataFlag.NONE),
            ("Picked", MetadataFlag.PICK),
            ("Rejected", MetadataFlag.REJECT),
        ], default_value=MetadataFlag.NONE)

        rows = [
            ("Title", self.metadata_title),
            ("Caption", self.metadata_caption),
            ("Creator", self.metadata_creator),
            ("Copyright", self.metadata_copyright),
            ("Supplemental categories CSV", self.metadata_supplemental_categories),
            ("Rating", self.metadata_rating),
            ("Color label", self.metadata_color_label),
            ("Flag", self.metadata_flag),
        ]
        for row, (label, widget) in enumerate(rows):
            form.addWidget(FieldLabel(label), row, 0)
            form.addWidget(widget, row, 1)
        box.layout().addLayout(form)

        self.metadata_rating.currentIndexChanged.connect(
            lambda _idx: self._write_single_metadata_field(
                MetadataField.RATING,
                self._combo_value(self.metadata_rating),
            )
        )
        self.metadata_color_label.currentIndexChanged.connect(
            lambda _idx: self._write_single_metadata_field(
                MetadataField.COLOR_LABEL,
                self._combo_value(self.metadata_color_label),
            )
        )
        self.metadata_flag.currentIndexChanged.connect(
            lambda _idx: self._write_single_metadata_field(
                MetadataField.FLAG,
                self._combo_value(self.metadata_flag),
            )
        )

        actions = QHBoxLayout()
        actions.setSpacing(8)
        buttons = [
            self.action_button("Read Metadata", self._read_metadata),
            self.action_button("Write Metadata", self._write_metadata),
            self.action_button("Read From File", self._read_metadata_from_file),
            self.action_button("Save To Sidecar", self._save_metadata_to_file),
        ]
        for button in buttons:
            actions.addWidget(button)
        actions.addStretch(1)
        box.layout().addLayout(actions)

        return box

    def _read_metadata(self) -> None:
        def call() -> object:
            return evoto.metadata.read(self._selected_ids())

        self._run("metadata.read", call)

    def _write_metadata(self) -> None:
        def call() -> object:
            return evoto.metadata.write(self._selected_ids(), self._metadata_fields())

        self._run("metadata.write", call)

    def _write_single_metadata_field(self, field: str, value: int) -> None:
        if not self.connect_bar.is_connected():
            return

        def call() -> object:
            return evoto.metadata.write(self._selected_ids(), {field: value})

        self._run(f"metadata.write.{field}", call)

    def _read_metadata_from_file(self) -> None:
        self._run(
            "metadata.read_from_file",
            lambda: evoto.metadata.read_from_file(self._selected_ids()),
        )

    def _save_metadata_to_file(self) -> None:
        self._run(
            "metadata.save_to_file",
            lambda: evoto.metadata.save_to_file(
                self._selected_ids(),
                sidecar=True,
                fields=self._metadata_fields(),
            ),
        )

    def _on_connected(self) -> None:
        super()._on_connected()
        self._register_file_events()

    def _on_disconnected(self) -> None:
        self._unregister_file_events()
        super()._on_disconnected()

    def _register_file_events(self) -> None:
        if self._file_event_callbacks:
            return
        for event_name in (
            "metadata.readFromFile.started",
            "metadata.readFromFile.progress",
            "metadata.readFromFile.completed",
            "metadata.readFromFile.failed",
            "metadata.saveToFile.started",
            "metadata.saveToFile.progress",
            "metadata.saveToFile.completed",
            "metadata.saveToFile.failed",
        ):
            def callback(data, _event_name=event_name):
                self.file_event_received.emit(_event_name, data or {})

            evoto.on(event_name, callback)
            self._file_event_callbacks.append((event_name, callback))

    def _unregister_file_events(self) -> None:
        for event_name, callback in self._file_event_callbacks:
            try:
                evoto.off(event_name, callback)
            except Exception as exc:  # noqa: BLE001 - disconnect cleanup best effort
                logger.debug("Failed to unsubscribe %s: %s", event_name, exc)
        self._file_event_callbacks.clear()

    def _on_file_event_main(self, event_name: str, data: object) -> None:
        if isinstance(data, dict):
            self._log(
                f"{event_name}: task_id={data.get('task_id', '-')}, "
                f"completed={data.get('completed_count', '-')}/"
                f"{data.get('requested_count', '-')}, "
                f"success={data.get('success_count', '-')}, "
                f"skipped={data.get('skipped_count', '-')}, "
                f"failed={data.get('failed_count', '-')}"
            )
            return
        self._log(f"{event_name}: {data}")

    def _supplemental_categories(self) -> list[str]:
        return [
            item.strip()
            for item in self.metadata_supplemental_categories.text().split(",")
            if item.strip()
        ]

    def _metadata_fields(self) -> dict:
        return {
            MetadataField.TITLE: self.metadata_title.text().strip(),
            MetadataField.CAPTION: self.metadata_caption.text().strip(),
            MetadataField.CREATOR: self.metadata_creator.text().strip(),
            MetadataField.COPYRIGHT: self.metadata_copyright.text().strip(),
            MetadataField.SUPPLEMENTAL_CATEGORIES: self._supplemental_categories(),
            MetadataField.RATING: self._combo_value(self.metadata_rating),
            MetadataField.COLOR_LABEL: self._combo_value(self.metadata_color_label),
            MetadataField.FLAG: self._combo_value(self.metadata_flag),
        }

    @staticmethod
    def _combo(items: list[tuple[str, int]], *, default_value: int) -> QComboBox:
        combo = QComboBox()
        for label, value in items:
            combo.addItem(label, value)
        index = combo.findData(default_value)
        if index >= 0:
            combo.setCurrentIndex(index)
        return combo

    @staticmethod
    def _combo_value(combo: QComboBox) -> int:
        return int(combo.currentData())


def main() -> int:
    app = QApplication(sys.argv)
    window = MetadataDemoWindow()
    apply_theme(window)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
