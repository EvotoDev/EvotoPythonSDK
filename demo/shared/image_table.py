"""Reusable image list/picker widget.

A self-contained panel that shows images of a given project in a table,
supports multi-row selection, and exposes a ``toolbar_layout`` so callers
can inject demo-specific action buttons (Import / Delete / Info / ...).

All demos that need to pick images from the current project should use
this widget instead of rebuilding their own ``QTableWidget``.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
)

import evoto


class ImageTable(QFrame):
    """Panel card with a refreshable image table bound to a project.

    Signals:
        log(str): log messages emitted by the widget.
        selection_changed(): fired when the set of selected rows changes.
        refresh_requested(): fired whenever a refresh starts (before loading).

    Public attributes (intended for callers to read):
        table (QTableWidget): the underlying table - use this if you need
            to attach a custom context menu or tweak selection programmatically.
        toolbar_layout (QHBoxLayout): empty horizontal layout sitting under
            the title row. Callers can append extra action buttons here
            (e.g. ``toolbar_layout.addWidget(my_btn)``).
    """

    log = Signal(str)
    selection_changed = Signal()
    refresh_requested = Signal()

    def __init__(
        self,
        *,
        title: str = 'IMAGES',
        hint: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._base_title = title
        self._project_id: int | None = None
        self._project_name: str = ''

        self.setObjectName('panelCard')
        self.setFrameShape(QFrame.StyledPanel)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 12)
        outer.setSpacing(8)

        head = QHBoxLayout()
        self._title_label = QLabel(self._base_title)
        self._title_label.setProperty('ev_role', 'section-title')
        head.addWidget(self._title_label)
        head.addStretch()
        self.btn_refresh = QPushButton('Refresh')
        self.btn_refresh.setProperty('ev_role', 'ghost')
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.clicked.connect(self.refresh)
        head.addWidget(self.btn_refresh)
        outer.addLayout(head)

        self.toolbar_layout = QHBoxLayout()
        self.toolbar_layout.setSpacing(6)
        self.toolbar_layout.setContentsMargins(0, 0, 0, 0)
        self._toolbar_host = QFrame()
        self._toolbar_host.setObjectName('imageTableToolbar')
        self._toolbar_host.setFrameShape(QFrame.NoFrame)
        # Use a targeted #id selector so only this frame goes transparent.
        # A bare ``QFrame { background: transparent; }`` would cascade to
        # child buttons and wipe the primary/etc. background colors,
        # leaving dark text on a dark surface.
        self._toolbar_host.setStyleSheet(
            'QFrame#imageTableToolbar { background: transparent; }'
        )
        self._toolbar_host.setLayout(self.toolbar_layout)
        self._toolbar_host.setVisible(False)
        outer.addWidget(self._toolbar_host)

        if hint:
            self._hint_label = QLabel(hint)
            self._hint_label.setProperty('ev_role', 'section-caption')
            outer.addWidget(self._hint_label)
        else:
            self._hint_label = None

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(['ID', 'Filename', 'Path'])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self.selection_changed)
        outer.addWidget(self.table, 1)

        self.stats_label = QLabel('')
        self.stats_label.setProperty('ev_role', 'section-caption')
        outer.addWidget(self.stats_label)

    # ------------------------------------------------------------ API --

    def add_toolbar_widget(self, widget) -> None:
        """Append *widget* to the internal toolbar row (shown automatically)."""
        self.toolbar_layout.addWidget(widget)
        self._toolbar_host.setVisible(True)

    def add_toolbar_stretch(self) -> None:
        self.toolbar_layout.addStretch()
        self._toolbar_host.setVisible(True)

    def set_hint(self, text: str | None) -> None:
        """Replace the hint label text (or remove it if *text* is falsy)."""
        if not text:
            if self._hint_label is not None:
                self._hint_label.hide()
            return
        if self._hint_label is None:
            self._hint_label = QLabel(text)
            self._hint_label.setProperty('ev_role', 'section-caption')
            self.layout().insertWidget(self.layout().count() - 2, self._hint_label)
        else:
            self._hint_label.setText(text)
            self._hint_label.show()

    @property
    def project_id(self) -> int | None:
        return self._project_id

    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable the refresh button (call when host connection flips)."""
        self.btn_refresh.setEnabled(enabled)

    def set_project(self, project_id: int | None, project_name: str = '') -> None:
        """Point the widget at a project and immediately reload its images."""
        self._project_id = int(project_id) if project_id else None
        self._project_name = project_name or ''
        self._update_title()
        self.refresh()

    def clear(self) -> None:
        """Reset rows, stats and project binding."""
        self._project_id = None
        self._project_name = ''
        self.table.setRowCount(0)
        self.stats_label.setText('')
        self._update_title()

    def refresh(self) -> None:
        """Re-fetch ``evoto.image.list`` for the current project id."""
        if not self._project_id:
            self.table.setRowCount(0)
            self.stats_label.setText('No project loaded')
            return

        self.refresh_requested.emit()
        try:
            images = evoto.image.list(project_id=self._project_id, data_mode=True)
        except Exception as exc:
            self.log.emit(f'Failed to load images: {exc}')
            self.stats_label.setText(f'Error: {exc}')
            return

        self.table.setRowCount(len(images))
        for row, img in enumerate(images):
            img_id = str(img.get('id', ''))
            img_name = img.get('filename', '')
            img_path = img.get('origin_path', '')
            self.table.setItem(row, 0, QTableWidgetItem(img_id))
            self.table.setItem(row, 1, QTableWidgetItem(str(img_name)))
            self.table.setItem(row, 2, QTableWidgetItem(str(img_path)))
        self.stats_label.setText(f'{len(images)} image(s) loaded')

    def selected_image_ids(self) -> list[int]:
        """Return integer IDs for every fully-selected row (in visual order)."""
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()})
        ids: list[int] = []
        for row in rows:
            item = self.table.item(row, 0)
            if item is None:
                continue
            try:
                ids.append(int(item.text()))
            except ValueError:
                pass
        return ids

    def all_image_ids(self) -> list[int]:
        """Return IDs of every currently loaded row (regardless of selection)."""
        ids: list[int] = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is None:
                continue
            try:
                ids.append(int(item.text()))
            except ValueError:
                pass
        return ids

    # ---------------------------------------------------------- internal --

    def _update_title(self) -> None:
        if self._project_id and self._project_name:
            self._title_label.setText(
                f'{self._base_title} - {self._project_name} (ID: {self._project_id})'
            )
        elif self._project_id:
            self._title_label.setText(f'{self._base_title} - Project {self._project_id}')
        else:
            self._title_label.setText(self._base_title)
