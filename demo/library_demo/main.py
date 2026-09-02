"""Library automation demo."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
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
from evoto.core.api_fields import LibraryField, MetadataColorLabel, MetadataFlag

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("library_demo")

_CHECK_GROUP_COLUMNS = 3


class LibraryDemoWindow(Phase2DemoWindow):
    """Dedicated LibraryAPI debug window."""

    switch_space_event = Signal(str, object)

    window_title = "Library Automation Demo"
    connect_title = "Library Automation Demo"
    image_hint = "Select rows before label or selection operations."

    def __init__(self):
        super().__init__()
        self.switch_space_event.connect(self._on_switch_space_event)
        evoto.library.on_switch_space_completed(
            lambda payload: self.switch_space_event.emit("library.switchSpace.completed", payload)
        )
        evoto.library.on_switch_space_failed(
            lambda payload: self.switch_space_event.emit("library.switchSpace.failed", payload)
        )

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
            title="LibraryAPI",
            subtitle="List filters / Update labels / Selection operations",
        )

        tab_row = QHBoxLayout()
        tab_row.setSpacing(8)
        self._library_tab_group = QButtonGroup(self)
        self.btn_tab_list_images = QPushButton("List Images")
        self.btn_tab_update_labels = QPushButton("Update Labels")
        self.btn_tab_selection = QPushButton("Selection")
        self.btn_tab_spaces = QPushButton("Spaces")
        for button in (
            self.btn_tab_list_images,
            self.btn_tab_update_labels,
            self.btn_tab_selection,
            self.btn_tab_spaces,
        ):
            button.setObjectName("taskSegBtn")
            button.setCheckable(True)
            button.setMinimumHeight(24)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._library_tab_group.addButton(self.btn_tab_list_images, 0)
        self._library_tab_group.addButton(self.btn_tab_update_labels, 1)
        self._library_tab_group.addButton(self.btn_tab_selection, 2)
        self._library_tab_group.addButton(self.btn_tab_spaces, 3)
        self.btn_tab_list_images.setChecked(True)
        tab_row.addWidget(self.btn_tab_list_images, 1)
        tab_row.addWidget(self.btn_tab_update_labels, 1)
        tab_row.addWidget(self.btn_tab_selection, 1)
        tab_row.addWidget(self.btn_tab_spaces, 1)
        box.layout().addLayout(tab_row)

        self._library_stack = QStackedWidget()
        self._library_stack.addWidget(self._build_list_images_page())
        self._library_stack.addWidget(self._build_update_labels_page())
        self._library_stack.addWidget(self._build_selection_page())
        self._library_stack.addWidget(self._build_spaces_page())
        self._library_tab_group.buttonClicked.connect(
            lambda button: self._library_stack.setCurrentIndex(
                self._library_tab_group.id(button)
            )
        )
        box.layout().addWidget(self._library_stack, 1)
        return box

    def _build_list_images_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(8)

        params_grid = QGridLayout()
        params_grid.setHorizontalSpacing(8)
        params_grid.setVerticalSpacing(10)
        params_grid.setColumnStretch(1, 1)

        filter_grid = QGridLayout()
        filter_grid.setContentsMargins(12, 6, 12, 12)
        filter_grid.setHorizontalSpacing(8)
        filter_grid.setVerticalSpacing(10)
        filter_grid.setColumnStretch(1, 1)

        self.library_page_size = QSpinBox()
        self.library_page_size.setRange(1, 500)
        self.library_page_size.setValue(50)
        self.library_page = QSpinBox()
        self.library_page.setRange(1, 999)
        self.library_page.setValue(1)
        self.filter_rating_widget, self.filter_rating_checks = self._check_group([
            ("0 star", 0),
            ("1 star", 1),
            ("2 stars", 2),
            ("3 stars", 3),
            ("4 stars", 4),
            ("5 stars", 5),
        ], default_values=[2, 3])
        self.filter_color_label_widget, self.filter_color_label_checks = self._check_group([
            ("None", MetadataColorLabel.NONE),
            ("Green", MetadataColorLabel.GREEN),
            ("Purple", MetadataColorLabel.PURPLE),
            ("Blue", MetadataColorLabel.BLUE),
            ("Yellow", MetadataColorLabel.YELLOW),
            ("Red", MetadataColorLabel.RED),
        ])
        self.filter_flag_widget, self.filter_flag_checks = self._check_group([
            ("Flagged", MetadataFlag.PICK),
            ("Rejected", MetadataFlag.REJECT),
            ("Unflagged", MetadataFlag.NONE),
        ], default_values=[MetadataFlag.PICK])
        self.filter_edit_status_widget, self.filter_edit_status_checks = self._check_group([
            ("Unedited", "unedited"),
            ("Edited", "edited"),
        ])
        self.filter_export_status_widget, self.filter_export_status_checks = self._check_group([
            ("Unexported", "unexported"),
            ("Exported", "exported"),
            ("Failed", "failed"),
        ])
        self.filter_format_widget, self.filter_format_checks = self._check_group([
            ("RAW", "RAW"),
            ("JPG", "JPG"),
            ("PNG", "PNG"),
            ("TIFF", "TIFF"),
            ("HEIC", "HEIC"),
            ("BMP", "BMP"),
        ])
        self.filter_orientation_widget, self.filter_orientation_checks = self._check_group([
            ("Landscape", "landscape"),
            ("Portrait", "portrait"),
            ("Square", "square"),
        ])
        self.library_file_name = QLineEdit("IMG,DSC")
        self.library_sort = self._combo([
            ("Capture time", LibraryField.CAPTURE_TIME),
            ("Filename", LibraryField.FILENAME),
            ("Rating", LibraryField.RATING),
            ("Color label", LibraryField.COLOR_LABEL),
        ], default_value=LibraryField.CAPTURE_TIME)
        self.library_sort_desc = QCheckBox("true")

        self.include_project_id = self._add_param_row(params_grid, 0, "Project ID", FieldLabel("Loaded project"), checked=True)
        self.include_sort = self._add_param_row(params_grid, 1, "Sort", self.library_sort, checked=False)
        self.include_sort_desc = self._add_param_row(params_grid, 2, "Descending", self.library_sort_desc, checked=False)
        self.include_page = self._add_param_row(params_grid, 3, "Page", self.library_page, checked=False)
        self.include_page_size = self._add_param_row(params_grid, 4, "Page Size", self.library_page_size, checked=False)

        self.include_rating = self._add_param_row(filter_grid, 0, "Rating", self.filter_rating_widget, checked=False)
        self.include_color_label = self._add_param_row(filter_grid, 1, "Color Label", self.filter_color_label_widget, checked=False)
        self.include_flag = self._add_param_row(filter_grid, 2, "Flag", self.filter_flag_widget, checked=False)
        self.include_edit_status = self._add_param_row(filter_grid, 3, "Edit Status", self.filter_edit_status_widget, checked=False)
        self.include_export_status = self._add_param_row(filter_grid, 4, "Export Status", self.filter_export_status_widget, checked=False)
        self.include_format = self._add_param_row(filter_grid, 5, "Format", self.filter_format_widget, checked=False)
        self.include_orientation = self._add_param_row(filter_grid, 6, "Orientation", self.filter_orientation_widget, checked=False)
        self.include_file_name = self._add_param_row(filter_grid, 7, "File Name", self.library_file_name, checked=False)

        filter_group = QGroupBox("Filter")
        filter_group.setLayout(filter_grid)

        grid_host = QWidget()
        grid_host.setObjectName("evParamHost")
        grid_host.setStyleSheet("QWidget#evParamHost { background: transparent; }")
        host_layout = QVBoxLayout(grid_host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(12)
        host_layout.addLayout(params_grid)
        host_layout.addWidget(filter_group)
        host_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setObjectName("evParamScroll")
        scroll.setWidget(grid_host)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # Scope transparency to the scroll frame and its viewport only, so
        # it never bleeds into child controls / combobox popups.
        scroll.setStyleSheet("QScrollArea#evParamScroll { background: transparent; }")
        scroll.viewport().setStyleSheet(
            "QWidget#qt_scrollarea_viewport { background: transparent; }"
        )
        page_layout.addWidget(scroll, 1)

        query_actions = QHBoxLayout()
        query_actions.setContentsMargins(0, 0, 0, 16)
        query_actions.setSpacing(8)
        list_button = self.action_button("List Images", self._list_images)
        list_button.setMinimumSize(180, 44)
        list_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        query_actions.addStretch(1)
        query_actions.addWidget(list_button)
        query_actions.addStretch(1)
        page_layout.addLayout(query_actions)
        return page

    def _build_update_labels_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(8)

        form = QGridLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(10)
        form.setColumnStretch(1, 1)

        self.library_rating = self._combo([
            ("No rating", 0),
            ("1 star", 1),
            ("2 stars", 2),
            ("3 stars", 3),
            ("4 stars", 4),
            ("5 stars", 5),
        ], default_value=5)
        self.library_color_label = self._combo([
            ("None", MetadataColorLabel.NONE),
            ("Green", MetadataColorLabel.GREEN),
            ("Purple", MetadataColorLabel.PURPLE),
            ("Blue", MetadataColorLabel.BLUE),
            ("Yellow", MetadataColorLabel.YELLOW),
            ("Red", MetadataColorLabel.RED),
        ], default_value=MetadataColorLabel.NONE)
        self.library_flag = self._combo([
            ("Unflagged", MetadataFlag.NONE),
            ("Picked", MetadataFlag.PICK),
            ("Rejected", MetadataFlag.REJECT),
        ], default_value=MetadataFlag.NONE)

        rows = [
            ("Rating", self.library_rating),
            ("Color label", self.library_color_label),
            ("Flag", self.library_flag),
        ]
        for row, (label, widget) in enumerate(rows):
            form.addWidget(FieldLabel(label), row, 0)
            form.addWidget(widget, row, 1)

        host = QWidget()
        host.setObjectName("evParamHost")
        host.setStyleSheet("QWidget#evParamHost { background: transparent; }")
        host_layout = QVBoxLayout(host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(12)
        host_layout.addLayout(form)
        host_layout.addStretch(1)

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

        query_actions = QHBoxLayout()
        query_actions.setContentsMargins(0, 0, 0, 16)
        query_actions.setSpacing(8)
        update_button = self.action_button("Update Labels", self._update_library_labels)
        update_button.setMinimumSize(180, 44)
        update_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        query_actions.addStretch(1)
        query_actions.addWidget(update_button)
        query_actions.addStretch(1)
        page_layout.addLayout(query_actions)
        return page

    def _build_selection_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 15, 0, 0)
        page_layout.setSpacing(12)

        selection_grid = QGridLayout()
        selection_grid.setHorizontalSpacing(8)
        selection_grid.setVerticalSpacing(10)
        selection_grid.setColumnStretch(1, 1)

        self.selection_set_ids = QComboBox()
        self.selection_add_ids = QLineEdit()
        self.selection_clear_ids = QLineEdit()
        for edit in (self.selection_add_ids, self.selection_clear_ids):
            edit.setPlaceholderText("Image IDs CSV, e.g. 100,101,102")

        rows = [
            (self.action_button("Get Selection", self._get_library_selection), None),
            (self.action_button("Set Selection", self._set_library_selection), self.selection_set_ids),
            (self.action_button("Add Selection", self._add_library_selection), self.selection_add_ids),
            (self.action_button("Clear Selection", self._clear_library_selection_ui), self.selection_clear_ids),
        ]
        for row, (button, edit) in enumerate(rows):
            selection_grid.addWidget(button, row, 0)
            if edit is not None:
                selection_grid.addWidget(edit, row, 1)

        self._refresh_selection_id_inputs()
        page_layout.addLayout(selection_grid)
        page_layout.addStretch(1)
        return page

    def _build_spaces_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 15, 0, 0)
        page_layout.setSpacing(12)

        form = QGridLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(10)
        form.setColumnStretch(1, 1)

        self.space_type_combo = self._combo([
            ("All spaces", "all"),
            ("Personal only", "personal"),
            ("Team only", "team"),
        ], default_value="all")
        self.space_type_combo.setEnabled(False)
        self.space_combo = QComboBox()
        self.space_combo.setEnabled(False)

        form.addWidget(FieldLabel("Space type"), 0, 0)
        form.addWidget(self.space_type_combo, 0, 1)
        form.addWidget(FieldLabel("Target space"), 1, 0)
        form.addWidget(self.space_combo, 1, 1)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addWidget(self.action_button("List Spaces", self._list_spaces))
        actions.addWidget(self.action_button("Current Space", self._current_space))
        actions.addWidget(self.action_button("Switch Space", self._switch_space))
        actions.addStretch(1)

        page_layout.addLayout(form)
        page_layout.addLayout(actions)
        page_layout.addStretch(1)
        return page

    def _list_images(self) -> None:
        def call() -> object:
            return evoto.library.list_images(
                self._project_id() if self.include_project_id.isChecked() else None,
                filters=self._library_filters(),
                sort=self._combo_value(self.library_sort) if self.include_sort.isChecked() else None,
                sort_desc=self.library_sort_desc.isChecked() if self.include_sort_desc.isChecked() else False,
                page=self.library_page.value() if self.include_page.isChecked() else None,
                page_size=self.library_page_size.value() if self.include_page_size.isChecked() else None,
            )

        self._run("library.list_images", call)

    def _update_library_labels(self) -> None:
        self._run(
            "library.update_labels",
            lambda: evoto.library.update_labels(
                self._selected_ids(),
                rating=self._combo_value(self.library_rating),
                color_label=self._combo_value(self.library_color_label),
                flag=self._combo_value(self.library_flag),
            ),
        )

    def _get_library_selection(self) -> None:
        self._run(
            "library.get_selection",
            lambda: evoto.library.get_selection(),
        )

    def _set_library_selection(self) -> None:
        image_ids = self._selection_ids_from_combo(self.selection_set_ids)
        self._run(
            "library.set_selection",
            lambda: evoto.library.set_selection(
                image_ids,
                primary_image_id=image_ids[0],
            ),
        )

    def _add_library_selection(self) -> None:
        image_ids = self._selection_ids_from_edit(self.selection_add_ids)
        self._run(
            "library.add_selection",
            lambda: evoto.library.add_selection(
                image_ids,
            ),
        )

    def _clear_library_selection_ui(self) -> None:
        image_ids = self._optional_selection_ids_from_edit(self.selection_clear_ids)
        self._run(
            "library.clear_selection",
            lambda: evoto.library.clear_selection(image_ids),
        )

    def _list_spaces(self) -> None:
        try:
            spaces = evoto.library.list_spaces(self._combo_value(self.space_type_combo))
            current = evoto.library.current_space()
            self._populate_space_combo(spaces, current)
            self._log(f"< library.list_spaces\n{self._pretty(spaces)}")
        except Exception as exc:
            self._log(f"! library.list_spaces failed: {exc}")

    def _current_space(self) -> None:
        self._run("library.current_space", lambda: evoto.library.current_space())

    def _switch_space(self) -> None:
        space_id = self.space_combo.currentData()
        if space_id is None:
            self._log("! library.switch_space failed: load spaces first.")
            return
        self._run("library.switch_space", lambda: evoto.library.switch_space(int(space_id)))

    def _on_switch_space_event(self, event_name: str, payload: object) -> None:
        self._log(f"< {event_name}\n{self._pretty(payload)}")
        if event_name == "library.switchSpace.completed":
            self._list_spaces()

    def _on_images_loaded(self, image_ids: list[int]) -> None:
        super()._on_images_loaded(image_ids)
        self._refresh_selection_id_inputs()

    def _on_connected(self) -> None:
        super()._on_connected()
        self.space_type_combo.setEnabled(True)
        self._list_spaces()

    def _on_disconnected(self) -> None:
        super()._on_disconnected()
        if getattr(self, "space_type_combo", None):
            self.space_type_combo.setEnabled(False)
        if getattr(self, "space_combo", None):
            self.space_combo.clear()
            self.space_combo.setEnabled(False)

    def _populate_space_combo(self, spaces: list[dict], current: dict | None = None) -> None:
        current = current or {}
        current_space_id = current.get(LibraryField.SPACE_ID)
        self.space_combo.blockSignals(True)
        self.space_combo.clear()
        for space in spaces:
            space_id = space.get(LibraryField.SPACE_ID)
            if space_id is None:
                continue
            space_type = space.get(LibraryField.TYPE)
            name = space.get(LibraryField.NAME, f"Space {space_id}")
            self.space_combo.addItem(f"{name} ({space_type}, ID: {space_id})", int(space_id))
            if current_space_id == space_id:
                self.space_combo.setCurrentIndex(self.space_combo.count() - 1)
        self.space_combo.setEnabled(self.space_combo.count() > 0)
        self.space_combo.blockSignals(False)

    def _library_filters(self) -> dict | None:
        filters = {}
        if self.include_rating.isChecked():
            values = self._checked_values(self.filter_rating_checks)
            if values:
                filters[LibraryField.RATING] = values
        if self.include_color_label.isChecked():
            values = self._checked_values(self.filter_color_label_checks)
            if values:
                filters[LibraryField.COLOR_LABEL] = values
        if self.include_flag.isChecked():
            values = self._checked_values(self.filter_flag_checks)
            if values:
                filters[LibraryField.FLAG] = values
        if self.include_edit_status.isChecked():
            values = self._checked_values(self.filter_edit_status_checks)
            if values:
                filters[LibraryField.EDIT_STATUS] = values
        if self.include_export_status.isChecked():
            values = self._checked_values(self.filter_export_status_checks)
            if values:
                filters[LibraryField.EXPORT_STATUS] = values
        if self.include_format.isChecked():
            values = self._checked_values(self.filter_format_checks)
            if values:
                filters[LibraryField.FORMAT] = values
        if self.include_orientation.isChecked():
            values = self._checked_values(self.filter_orientation_checks)
            if values:
                filters[LibraryField.ORIENTATION] = values
        if self.include_file_name.isChecked():
            values = self._csv_values(self.library_file_name.text())
            if values:
                filters[LibraryField.FILE_NAME] = values
        return filters or None

    @staticmethod
    def _check_group(
        options: list[tuple[str, Any]],
        *,
        default_values: list[Any] | None = None,
    ) -> tuple[QWidget, list[tuple[QCheckBox, Any]]]:
        widget = QWidget()
        widget.setObjectName("evCheckGroup")
        # Scope the transparent fill to this container only - a bare
        # ``background: transparent`` would cascade into child widgets
        # (and a QComboBox's popup), painting their backgrounds white.
        widget.setStyleSheet("QWidget#evCheckGroup { background: transparent; }")
        layout = QGridLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(28)
        layout.setVerticalSpacing(8)

        defaults = set(default_values or [])
        checks: list[tuple[QCheckBox, Any]] = []
        for index, (label, value) in enumerate(options):
            check = QCheckBox(label)
            check.setChecked(value in defaults)
            # The themed 16px indicator makes QCheckBox.sizeHint under-
            # estimate the needed width/height by a pixel or two, clipping
            # the last glyph ("Flagged" -> "Flagg") and the indicator top.
            # Reserve room explicitly from font metrics instead.
            fm = check.fontMetrics()
            text_width = fm.horizontalAdvance(label)
            check.setMinimumWidth(text_width + 16 + 6 + 8)  # indicator + spacing + buffer
            check.setMinimumHeight(max(fm.height(), 16) + 6)
            row, col = divmod(index, _CHECK_GROUP_COLUMNS)
            layout.addWidget(check, row, col)
            checks.append((check, value))
        # Trailing stretch column soaks up slack so the checkbox columns
        # stay left-aligned with the fixed inter-column gap above instead
        # of spreading edge-to-edge.
        last_col = min(len(options), _CHECK_GROUP_COLUMNS)
        layout.setColumnStretch(last_col, 1)
        return widget, checks

    @staticmethod
    def _checked_values(checks: list[tuple[QCheckBox, Any]]) -> list[Any]:
        return [value for check, value in checks if check.isChecked()]

    @staticmethod
    def _csv_values(text: str) -> list[str]:
        return [part.strip() for part in text.split(",") if part.strip()]

    def _refresh_selection_id_inputs(self) -> None:
        if not hasattr(self, "selection_set_ids"):
            return
        if self.loader.image_ids:
            image_ids = self.loader.image_ids
        else:
            image_ids = self.image_table.all_image_ids()

        self.selection_set_ids.clear()
        for image_id in image_ids[:10]:
            self.selection_set_ids.addItem(str(image_id), image_id)

        text = ",".join(str(image_id) for image_id in image_ids[:3])
        self.selection_add_ids.setText(text)
        self.selection_clear_ids.setText(text)

    def _selection_ids_from_edit(self, edit: QLineEdit) -> list[int]:
        return self._selection_ids_from_text(edit.text())

    def _optional_selection_ids_from_edit(self, edit: QLineEdit) -> list[int] | None:
        if not edit.text().strip():
            return None
        return self._selection_ids_from_edit(edit)

    def _selection_ids_from_combo(self, combo: QComboBox) -> list[int]:
        image_id = combo.currentData()
        if image_id is None:
            raise RuntimeError("Select an image ID.")
        return [int(image_id)]

    def _selection_ids_from_text(self, text: str) -> list[int]:
        values = self._csv_values(text)
        if not values:
            raise RuntimeError("Enter at least one image ID.")
        try:
            return [int(value) for value in values]
        except ValueError as exc:
            raise RuntimeError("Image IDs must be comma-separated integers.") from exc

    @staticmethod
    def _add_param_row(grid: QGridLayout, row: int, name: str, widget: QWidget, *, checked: bool) -> QCheckBox:
        include = QCheckBox(name)
        include.setChecked(checked)
        # The themed 16px indicator makes QCheckBox.sizeHint under-estimate
        # the label width, clipping the last glyph ("Descending"). Reserve
        # room explicitly from font metrics.
        fm = include.fontMetrics()
        include.setMinimumWidth(fm.horizontalAdvance(name) + 16 + 6 + 8)
        grid.addWidget(include, row, 0)
        grid.addWidget(widget, row, 1)
        return include


def main() -> int:
    app = QApplication(sys.argv)
    window = LibraryDemoWindow()
    apply_theme(window)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
