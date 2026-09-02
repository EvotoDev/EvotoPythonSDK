"""Mapping table widget - one row per watch->export lane.

Columns (left->right):
    0  Label      line-edit
    1  Watch      combo-box bound to the global watch-folder list
    2  Export     folder path + Browse
    3  Preset     button showing current preset name (opens PresetPickerDialog)
    4  Options    button with a short summary (opens OptionsDialog)
    5  Status     read-only text (set by the pipeline)
    6  Delete     ghost button

A row is considered active as soon as it has a watch folder, an
export folder, and at least one preset suit - there's no separate
on/off toggle. Remove the row (or clear one of those fields) to pause
a lane.

The table owns the live list of :class:`MappingRow`. Call
:meth:`rows` to snapshot it back into the config.

The watch-folder options are supplied by the host through
:meth:`set_watch_paths` - typically driven by the shared
:class:`WatchConfigPanel`. This keeps the global watcher config and
the per-row routing in lockstep.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QWidget,
)

from demo.hot_folder_demo.config import MappingRow
from demo.hot_folder_demo.options_dialog import OptionsDialog
from demo.hot_folder_demo.preset_picker_dialog import PresetPickerDialog


_COL_LABEL, _COL_WATCH, _COL_EXPORT, \
    _COL_PRESET, _COL_OPTIONS, _COL_STATUS, _COL_DEL = range(7)


def _path_cell(initial: str, on_pick: Callable[[str], None]) -> QWidget:
    """Compose a path line-edit + Browse button into one cell widget."""
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(4, 2, 4, 2)
    lay.setSpacing(4)

    edit = QLineEdit(initial)
    edit.setPlaceholderText('/abs/path')
    lay.addWidget(edit, 1)

    btn = QPushButton('...')
    btn.setProperty('ev_role', 'ghost')
    btn.setFixedWidth(30)
    lay.addWidget(btn)

    def _do_browse():
        path = QFileDialog.getExistingDirectory(w, 'Select folder', edit.text() or '')
        if path:
            edit.setText(path)
            on_pick(path)

    btn.clicked.connect(_do_browse)
    edit.editingFinished.connect(lambda: on_pick(edit.text().strip()))

    w.setProperty('line_edit', edit)
    return w


class MappingTable(QTableWidget):
    """QTableWidget bound to a list of :class:`MappingRow`."""

    rows_changed = Signal()

    _HEADERS = ['Label', 'Watch Folder', 'Export Folder',
               'Preset Suit', 'Options', 'Status', '']

    def __init__(self, parent=None):
        super().__init__(0, len(self._HEADERS), parent)
        self._rows: list[MappingRow] = []
        self._watch_paths: list[str] = []

        self.setHorizontalHeaderLabels(self._HEADERS)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(40)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionMode(QTableWidget.NoSelection)
        self.setShowGrid(False)

        h = self.horizontalHeader()
        h.setSectionResizeMode(_COL_LABEL,   QHeaderView.Interactive)
        h.resizeSection(_COL_LABEL, 120)
        h.setSectionResizeMode(_COL_WATCH,   QHeaderView.Stretch)
        h.setSectionResizeMode(_COL_EXPORT,  QHeaderView.Stretch)
        h.setSectionResizeMode(_COL_PRESET,  QHeaderView.Interactive)
        h.resizeSection(_COL_PRESET, 160)
        h.setSectionResizeMode(_COL_OPTIONS, QHeaderView.Interactive)
        h.resizeSection(_COL_OPTIONS, 140)
        h.setSectionResizeMode(_COL_STATUS,  QHeaderView.Interactive)
        h.resizeSection(_COL_STATUS, 120)
        h.setSectionResizeMode(_COL_DEL,     QHeaderView.Fixed)
        # 54px clipped "Remove" behind the button padding - the label
        # needs ~60px on its own and the QPushButton adds 10px padding
        # on each side. Round up a bit so the cell has breathing room.
        h.resizeSection(_COL_DEL, 96)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_rows(self, rows: list[MappingRow]) -> None:
        self._rows = [self._clone_row(r) for r in rows]
        self._repaint()

    def rows(self) -> list[MappingRow]:
        return [self._clone_row(r) for r in self._rows]

    @staticmethod
    def _clone_row(r: MappingRow) -> MappingRow:
        """Deep-enough copy so the caller can't mutate our live state by
        holding onto a returned ``MappingRow`` reference."""
        return MappingRow(
            id=r.id, label=r.label,
            watch_folder=r.watch_folder, export_folder=r.export_folder,
            preset_suit_ids=list(r.preset_suit_ids or []),
            preset_suit_names=list(r.preset_suit_names or []),
            export_options=dict(r.export_options or {}),
        )

    def add_row(self, row: MappingRow | None = None) -> None:
        self._rows.append(row or MappingRow())
        self._repaint()
        self.rows_changed.emit()

    def set_status(self, row_id: str, text: str) -> None:
        for i, r in enumerate(self._rows):
            if r.id == row_id:
                item = self.item(i, _COL_STATUS)
                if item is None:
                    item = QTableWidgetItem(text)
                    item.setFlags(Qt.ItemIsEnabled)
                    self.setItem(i, _COL_STATUS, item)
                else:
                    item.setText(text)
                return

    def set_all_status(self, text: str) -> None:
        for i in range(len(self._rows)):
            item = self.item(i, _COL_STATUS)
            if item is None:
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemIsEnabled)
                self.setItem(i, _COL_STATUS, item)
            else:
                item.setText(text)

    def set_editable(self, editable: bool) -> None:
        """Disable edits while the pipeline is running (still show data)."""
        for i in range(self.rowCount()):
            for c in (_COL_LABEL, _COL_WATCH, _COL_EXPORT,
                      _COL_PRESET, _COL_OPTIONS, _COL_DEL):
                widget = self.cellWidget(i, c)
                if widget is not None:
                    widget.setEnabled(editable)

    def set_watch_paths(self, paths: list[str]) -> None:
        """Update the Watch Folder combos after the global list changed.

        Each row's current selection is preserved when possible. If a
        row references a folder that was just removed, the missing path
        is still shown (suffixed with " (missing)") so the user can see
        the broken link and fix it explicitly.
        """
        self._watch_paths = [p for p in dict.fromkeys(paths) if p]
        for i in range(self.rowCount()):
            combo = self.cellWidget(i, _COL_WATCH)
            if isinstance(combo, QComboBox):
                row = self._rows[i]
                self._populate_watch_combo(combo, row.watch_folder)

    # ------------------------------------------------------------------
    # Cell construction
    # ------------------------------------------------------------------

    def _populate_watch_combo(self, combo: QComboBox, selected: str) -> None:
        """Rebuild *combo* from the global watch-path list.

        Items store the full path in ``userData`` so it survives even
        when the label gets decorated (e.g. "(missing)").
        """
        combo.blockSignals(True)
        combo.clear()
        combo.addItem('- pick a watch folder -', '')
        for p in self._watch_paths:
            combo.addItem(p, p)
        # Surface rows whose saved path is no longer in the global list,
        # so the user can notice and fix it rather than silently losing
        # the routing.
        if selected and selected not in self._watch_paths:
            combo.addItem(f'{selected}  (missing)', selected)

        target = selected or ''
        idx = 0
        for i in range(combo.count()):
            if combo.itemData(i) == target:
                idx = i
                break
        combo.setCurrentIndex(idx)
        combo.blockSignals(False)

    def _repaint(self) -> None:
        self.setRowCount(0)
        for i, r in enumerate(self._rows):
            self.insertRow(i)
            self._render_row(i, r)

    def _render_row(self, i: int, r: MappingRow) -> None:
        # Label ----------------------------------------------------------
        label_edit = QLineEdit(r.label)
        label_edit.setPlaceholderText('Lane name')
        label_edit.editingFinished.connect(
            lambda le=label_edit, rr=r: self._on_label(rr, le.text()))
        self.setCellWidget(i, _COL_LABEL, label_edit)

        # Watch folder ---------------------------------------------------
        watch_combo = QComboBox()
        self._populate_watch_combo(watch_combo, r.watch_folder)
        watch_combo.currentIndexChanged.connect(
            lambda _idx, cb=watch_combo, rr=r: self._on_watch(
                rr, cb.currentData() or ''))
        self.setCellWidget(i, _COL_WATCH, watch_combo)

        # Export folder --------------------------------------------------
        export_cell = _path_cell(
            r.export_folder,
            on_pick=lambda p, rr=r: self._on_export(rr, p),
        )
        self.setCellWidget(i, _COL_EXPORT, export_cell)

        # Preset button --------------------------------------------------
        preset_btn = QPushButton(self._preset_label(r))
        preset_btn.setToolTip(self._preset_tooltip(r))
        preset_btn.clicked.connect(lambda _, rr=r, b=preset_btn: self._on_preset(rr, b))
        self.setCellWidget(i, _COL_PRESET, preset_btn)

        # Options button -------------------------------------------------
        opts_btn = QPushButton(OptionsDialog.summary(r.export_options))
        opts_btn.setProperty('ev_role', 'ghost')
        opts_btn.clicked.connect(lambda _, rr=r, b=opts_btn: self._on_options(rr, b))
        self.setCellWidget(i, _COL_OPTIONS, opts_btn)

        # Status ---------------------------------------------------------
        status_item = QTableWidgetItem('idle')
        status_item.setFlags(Qt.ItemIsEnabled)
        self.setItem(i, _COL_STATUS, status_item)

        # Delete ---------------------------------------------------------
        # Wrap in a small container so the button isn't flush against
        # the cell borders - the 4px margin matches the other action
        # cells (Watch / Export) and keeps "Remove" fully visible.
        del_wrap = QWidget()
        del_lay = QHBoxLayout(del_wrap)
        del_lay.setContentsMargins(4, 2, 4, 2)
        del_lay.setSpacing(0)
        del_btn = QPushButton('Remove')
        del_btn.setProperty('ev_role', 'ghost')
        del_btn.clicked.connect(lambda _, rr=r: self._on_remove(rr))
        del_lay.addWidget(del_btn)
        self.setCellWidget(i, _COL_DEL, del_wrap)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_label(self, row: MappingRow, text: str) -> None:
        row.label = text.strip()
        self.rows_changed.emit()

    def _on_watch(self, row: MappingRow, path: str) -> None:
        row.watch_folder = path
        self.rows_changed.emit()

    def _on_export(self, row: MappingRow, path: str) -> None:
        row.export_folder = path
        self.rows_changed.emit()

    def _on_preset(self, row: MappingRow, btn: QPushButton) -> None:
        dlg = PresetPickerDialog(
            current_ids=row.preset_suit_ids, parent=self)
        if dlg.exec() != dlg.Accepted:
            return
        sel = dlg.selection()
        if not sel:
            return
        ids, names = sel
        row.preset_suit_ids = list(ids)
        row.preset_suit_names = list(names)
        btn.setText(self._preset_label(row))
        btn.setToolTip(self._preset_tooltip(row))
        self.rows_changed.emit()

    # ------------------------------------------------------------------
    # Label helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _preset_label(r: MappingRow) -> str:
        """Compact one-line text for the Preset Suit cell button."""
        names = [n for n in (r.preset_suit_names or []) if n]
        if not names:
            return 'Pick preset(s)...'
        if len(names) == 1:
            return names[0]
        # Keep the button readable in a narrow column: show the first
        # name and a "+N" badge for the rest; the tooltip spells out
        # every suit.
        return f'{names[0]} +{len(names) - 1}'

    @staticmethod
    def _preset_tooltip(r: MappingRow) -> str:
        names = [n for n in (r.preset_suit_names or []) if n]
        if not names:
            return ''
        return '\n'.join(names)

    def _on_options(self, row: MappingRow, btn: QPushButton) -> None:
        dlg = OptionsDialog(row.export_options, parent=self)
        if dlg.exec() != dlg.Accepted:
            return
        row.export_options = dlg.result_options()
        btn.setText(OptionsDialog.summary(row.export_options))
        self.rows_changed.emit()

    def _on_remove(self, row: MappingRow) -> None:
        self._rows = [r for r in self._rows if r.id != row.id]
        self._repaint()
        self.rows_changed.emit()
