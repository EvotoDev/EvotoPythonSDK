"""Edit recipe automation demo."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import evoto
from demo.shared import Card, FieldLabel, Phase2DemoWindow, apply_theme
from evoto.core.api_fields import EditModuleValue

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("edit_recipe_demo")

_MODULE_COLUMNS = 3
_EDIT_MODULES = [
    ("Color", EditModuleValue.COLOR),
    ("AI Color", EditModuleValue.AI_COLOR),
    ("Portrait", EditModuleValue.PORTRAIT),
    ("Background", EditModuleValue.BACKGROUND),
    ("Crop", EditModuleValue.CROP),
    ("Clothes", EditModuleValue.CLOTHES),
    ("Pet", EditModuleValue.PET),
]


class EditRecipeDemoWindow(Phase2DemoWindow):
    """Dedicated EditAPI debug window."""

    window_title = "Edit Recipe Demo"
    connect_title = "Edit Recipe Demo"
    image_hint = "Use image IDs for status, sync, reset, and virtual copy testing."

    def _build_right_panel(self) -> QWidget:
        right = QWidget()
        layout = QVBoxLayout(right)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self.build_actions_panel(), 3)
        layout.addWidget(self._build_log_panel(), 2)
        return right

    def build_actions_panel(self) -> QWidget:
        box = Card(
            title="EditAPI",
            subtitle="Inspect edit status, sync modules, reset modules, create virtual copies",
        )

        tab_row = QHBoxLayout()
        tab_row.setSpacing(8)
        self._edit_tab_group = QButtonGroup(self)
        self.btn_tab_inspect = QPushButton("Inspect")
        self.btn_tab_sync = QPushButton("Sync")
        self.btn_tab_reset_copy = QPushButton("Reset / Copy")
        for button in (self.btn_tab_inspect, self.btn_tab_sync, self.btn_tab_reset_copy):
            button.setObjectName("taskSegBtn")
            button.setCheckable(True)
            button.setMinimumHeight(24)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._edit_tab_group.addButton(self.btn_tab_inspect, 0)
        self._edit_tab_group.addButton(self.btn_tab_sync, 1)
        self._edit_tab_group.addButton(self.btn_tab_reset_copy, 2)
        self.btn_tab_inspect.setChecked(True)
        tab_row.addWidget(self.btn_tab_inspect, 1)
        tab_row.addWidget(self.btn_tab_sync, 1)
        tab_row.addWidget(self.btn_tab_reset_copy, 1)
        box.layout().addLayout(tab_row)

        self._edit_stack = QStackedWidget()
        self._edit_stack.addWidget(self._build_inspect_page())
        self._edit_stack.addWidget(self._build_sync_page())
        self._edit_stack.addWidget(self._build_reset_copy_page())
        self._edit_tab_group.buttonClicked.connect(
            lambda button: self._edit_stack.setCurrentIndex(self._edit_tab_group.id(button))
        )
        box.layout().addWidget(self._edit_stack, 1)

        hint = QLabel(
            "Mutation workflows return accepted/skipped/failed counts. "
            "Guarded host-only flows report a skipped reason instead of partial DB-only changes."
        )
        hint.setProperty("ev_role", "section-caption")
        box.layout().addWidget(hint)
        return box

    def _build_inspect_page(self) -> QWidget:
        page, layout = self._scroll_page()

        form = QGridLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(10)
        form.setColumnStretch(1, 1)

        self.status_image_ids = QLineEdit()
        self.status_image_ids.setPlaceholderText("Optional image IDs CSV. Empty = all project images")
        form.addWidget(FieldLabel("Image IDs"), 0, 0)
        form.addWidget(self.status_image_ids, 0, 1)
        layout.addLayout(form)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 8, 0, 16)
        actions.setSpacing(12)
        status_btn = self._large_action_button("Edit Status", self._edit_status)
        actions.addStretch(1)
        actions.addWidget(status_btn)
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addStretch(1)
        return page

    def _build_sync_page(self) -> QWidget:
        page, layout = self._scroll_page()

        form = QGridLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(10)
        form.setColumnStretch(1, 1)

        self.sync_source_id = QComboBox()
        self.sync_target_ids = QLineEdit()
        self.sync_target_ids.setPlaceholderText("Target image IDs CSV, e.g. 102,103,104")
        self.sync_modules_widget, self.sync_module_checks = self._module_group(
            default_values=[EditModuleValue.COLOR, EditModuleValue.PORTRAIT],
        )

        form.addWidget(FieldLabel("Source Image"), 0, 0)
        form.addWidget(self.sync_source_id, 0, 1)
        form.addWidget(FieldLabel("Target IDs"), 1, 0)
        form.addWidget(self.sync_target_ids, 1, 1)
        module_group = QGroupBox("Modules")
        module_layout = QVBoxLayout(module_group)
        module_layout.setContentsMargins(12, 8, 12, 12)
        module_layout.addWidget(self.sync_modules_widget)
        form.addWidget(FieldLabel("Sync Modules"), 2, 0)
        form.addWidget(module_group, 2, 1)
        layout.addLayout(form)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 8, 0, 16)
        sync_btn = self._large_action_button("Sync From", self._edit_sync)
        actions.addStretch(1)
        actions.addWidget(sync_btn)
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addStretch(1)
        return page

    def _build_reset_copy_page(self) -> QWidget:
        page, layout = self._scroll_page()

        reset_group = QGroupBox("Reset Modules")
        reset_layout = QGridLayout(reset_group)
        reset_layout.setContentsMargins(12, 8, 12, 12)
        reset_layout.setHorizontalSpacing(8)
        reset_layout.setVerticalSpacing(10)
        reset_layout.setColumnStretch(1, 1)

        self.reset_image_ids = QLineEdit()
        self.reset_image_ids.setPlaceholderText("Image IDs CSV, e.g. 100,101,102")
        self.reset_modules_widget, self.reset_module_checks = self._module_group(
            default_values=[EditModuleValue.BACKGROUND],
        )
        reset_layout.addWidget(FieldLabel("Image IDs"), 0, 0)
        reset_layout.addWidget(self.reset_image_ids, 0, 1)
        reset_layout.addWidget(FieldLabel("Modules"), 1, 0)
        reset_layout.addWidget(self.reset_modules_widget, 1, 1)
        reset_actions = QHBoxLayout()
        reset_actions.addStretch(1)
        reset_actions.addWidget(self._large_action_button("Reset Modules", self._edit_reset))
        reset_actions.addStretch(1)
        reset_layout.addLayout(reset_actions, 2, 0, 1, 2)
        layout.addWidget(reset_group)

        copy_group = QGroupBox("Virtual Copy")
        copy_layout = QGridLayout(copy_group)
        copy_layout.setContentsMargins(12, 8, 12, 12)
        copy_layout.setHorizontalSpacing(8)
        copy_layout.setVerticalSpacing(10)
        copy_layout.setColumnStretch(1, 1)

        self.copy_source_id = QComboBox()
        copy_layout.addWidget(FieldLabel("Source Image"), 0, 0)
        copy_layout.addWidget(self.copy_source_id, 0, 1)
        copy_actions = QHBoxLayout()
        copy_actions.addStretch(1)
        copy_actions.addWidget(self._large_action_button("Create Virtual Copy", self._edit_virtual_copy))
        copy_actions.addStretch(1)
        copy_layout.addLayout(copy_actions, 1, 0, 1, 2)
        layout.addWidget(copy_group)
        layout.addStretch(1)
        return page

    def _edit_status(self) -> None:
        image_ids = self._optional_ids_from_edit(self.status_image_ids)
        self._run("edit.status", lambda: evoto.edit.status(self._project_id(), image_ids=image_ids))

    def _edit_sync(self) -> None:
        def call() -> object:
            return evoto.edit.sync_from(
                self._combo_int(self.sync_source_id),
                self._ids_from_edit(self.sync_target_ids),
                modules=self._checked_modules(self.sync_module_checks),
            )

        self._run("edit.sync_from", call)

    def _edit_reset(self) -> None:
        self._run(
            "edit.reset",
            lambda: evoto.edit.reset(
                self._ids_from_edit(self.reset_image_ids),
                modules=self._checked_modules(self.reset_module_checks),
            ),
        )

    def _edit_virtual_copy(self) -> None:
        self._run(
            "edit.create_virtual_copy",
            lambda: evoto.edit.create_virtual_copy(self._combo_int(self.copy_source_id)),
        )

    def _on_images_loaded(self, image_ids: list[int]) -> None:
        super()._on_images_loaded(image_ids)
        self._refresh_edit_inputs()

    def _refresh_edit_inputs(self) -> None:
        if not hasattr(self, "sync_source_id"):
            return
        image_ids = self.loader.image_ids or self.image_table.all_image_ids()
        for combo in (self.sync_source_id, self.copy_source_id):
            combo.clear()
            for image_id in image_ids[:10]:
                combo.addItem(str(image_id), image_id)

        self.status_image_ids.setText(",".join(str(image_id) for image_id in image_ids[:3]))
        target_ids = image_ids[1:4] if len(image_ids) > 1 else image_ids[:1]
        self.sync_target_ids.setText(",".join(str(image_id) for image_id in target_ids))
        self.reset_image_ids.setText(",".join(str(image_id) for image_id in image_ids[:3]))

    @staticmethod
    def _scroll_page() -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        host = QWidget()
        host.setObjectName("evParamHost")
        host.setStyleSheet("QWidget#evParamHost { background: transparent; }")
        host_layout = QVBoxLayout(host)
        host_layout.setContentsMargins(0, 10, 0, 0)
        host_layout.setSpacing(12)

        scroll = QScrollArea()
        scroll.setObjectName("evParamScroll")
        scroll.setWidget(host)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea#evParamScroll { background: transparent; }")
        scroll.viewport().setStyleSheet(
            "QWidget#qt_scrollarea_viewport { background: transparent; }"
        )
        page_layout.addWidget(scroll, 1)
        return page, host_layout

    def _large_action_button(self, text: str, handler) -> QPushButton:
        button = self.action_button(text, handler)
        button.setMinimumSize(180, 44)
        button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        return button

    @staticmethod
    def _module_group(
        *,
        default_values: list[str] | None = None,
    ) -> tuple[QWidget, list[tuple[QCheckBox, str]]]:
        widget = QWidget()
        widget.setObjectName("evCheckGroup")
        widget.setStyleSheet("QWidget#evCheckGroup { background: transparent; }")
        layout = QGridLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(24)
        layout.setVerticalSpacing(8)

        defaults = set(default_values or [])
        checks: list[tuple[QCheckBox, str]] = []
        for index, (label, value) in enumerate(_EDIT_MODULES):
            check = QCheckBox(label)
            check.setChecked(value in defaults)
            row, col = divmod(index, _MODULE_COLUMNS)
            layout.addWidget(check, row, col)
            checks.append((check, value))
        layout.setColumnStretch(_MODULE_COLUMNS, 1)
        return widget, checks

    @staticmethod
    def _checked_modules(checks: list[tuple[QCheckBox, str]]) -> list[str]:
        return [value for check, value in checks if check.isChecked()]

    @staticmethod
    def _ids_from_edit(edit: QLineEdit) -> list[int]:
        values = [part.strip() for part in edit.text().split(",") if part.strip()]
        if not values:
            raise RuntimeError("Enter at least one image ID.")
        try:
            return [int(value) for value in values]
        except ValueError as exc:
            raise RuntimeError("Image IDs must be comma-separated integers.") from exc

    @staticmethod
    def _optional_ids_from_edit(edit: QLineEdit) -> list[int] | None:
        values = [part.strip() for part in edit.text().split(",") if part.strip()]
        if not values:
            return None
        try:
            return [int(value) for value in values]
        except ValueError as exc:
            raise RuntimeError("Image IDs must be comma-separated integers.") from exc

    @staticmethod
    def _combo_int(combo: QComboBox) -> int:
        value = combo.currentData()
        if value is None:
            raise RuntimeError("Select an image ID.")
        return int(value)


def main() -> int:
    app = QApplication(sys.argv)
    window = EditRecipeDemoWindow()
    apply_theme(window)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
