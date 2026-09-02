"""Shared watcher configuration panel.

Packages the UI for every parameter ``evoto.watcher.start()`` accepts:

- a list of watch folder paths (managed via a table + Add/Remove),
- the ``include_sub_dir`` toggle,
- the per-extension ``filters`` list (JPG / PNG / TIFF / RAW).

Demos drop this panel into their layout, add a Start/Stop button of
their choice via :meth:`add_header_action`, and react to
:attr:`paths_changed` / :attr:`settings_changed` /
:attr:`refresh_requested` to drive the host-side watcher.
"""

from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from .theme import fix_checkbox_width


try:
    from evoto.watcher import WatchFilterType
    _FILTER_CHOICES: tuple[tuple[str, str], ...] = (
        ('JPG',  WatchFilterType.JPG.value),
        ('PNG',  WatchFilterType.PNG.value),
        ('TIFF', WatchFilterType.TIFF.value),
        ('RAW',  WatchFilterType.RAW.value),
    )
except ImportError:  # SDK-less unit tests
    _FILTER_CHOICES = (
        ('JPG', 'jpg'), ('PNG', 'png'), ('TIFF', 'tiff'), ('RAW', 'raw'),
    )


class WatchConfigPanel(QFrame):
    """Reusable watcher configuration panel.

    Signals:
        paths_changed(list): the watch-folder list was edited.
        settings_changed(): the subdir toggle or a filter checkbox flipped.
        refresh_requested(): the user clicked the "Refresh Status" button.
    """

    paths_changed = Signal(list)
    settings_changed = Signal()
    refresh_requested = Signal()

    def __init__(self, title: str = 'WATCH FOLDERS', parent=None):
        super().__init__(parent)
        self.setObjectName('panelCard')
        self.setFrameShape(QFrame.StyledPanel)

        self._paths: list[str] = []
        self._filter_checks: dict[str, QCheckBox] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 12)
        root.setSpacing(8)

        # ── Header row: title + status + refresh + host-supplied actions.
        head = QHBoxLayout()
        head.setSpacing(10)
        self._title = QLabel(title)
        self._title.setProperty('ev_role', 'section-title')
        head.addWidget(self._title)

        head.addStretch(1)

        self._status = QLabel('')
        self._status.setProperty('ev_role', 'section-caption')
        self._status.setVisible(False)
        head.addWidget(self._status)

        self.btn_refresh = QPushButton('Refresh')
        self.btn_refresh.setProperty('ev_role', 'ghost')
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.clicked.connect(self.refresh_requested.emit)
        head.addWidget(self.btn_refresh)

        self._header_actions = head  # host calls add_header_action() to push
        root.addLayout(head)

        # ── Folders table ─────────────────────────────────────────────
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(['Path', ''])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        h.setSectionResizeMode(1, QHeaderView.Fixed)
        h.resizeSection(1, 90)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        root.addWidget(self.table, 1)

        # ── Filter row (sits above Add Folder so its checkbox labels
        # always fit regardless of panel width). ─────────────────────
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        for label, value in _FILTER_CHOICES:
            chk = QCheckBox(label)
            chk.setChecked(True)
            fix_checkbox_width(chk)
            chk.toggled.connect(self.settings_changed.emit)
            filter_row.addWidget(chk)
            self._filter_checks[value] = chk

        filter_row.addStretch(1)
        root.addLayout(filter_row)

        # ── Action row: include_sub_dir on the left, Add Folder pinned
        # to the right so it lines up with the table's right edge. ───
        footer = QHBoxLayout()
        footer.setSpacing(10)

        self.chk_sub_dir = QCheckBox('Include sub-folders')
        self.chk_sub_dir.setChecked(True)
        fix_checkbox_width(self.chk_sub_dir)
        self.chk_sub_dir.toggled.connect(self.settings_changed.emit)
        footer.addWidget(self.chk_sub_dir)

        footer.addStretch(1)

        self.btn_add = QPushButton('Add Folder')
        self.btn_add.setProperty('ev_role', 'ghost')
        self.btn_add.clicked.connect(self._on_add_folder)
        footer.addWidget(self.btn_add)

        root.addLayout(footer)

    # ------------------------------------------------------------------
    # Host-facing API - paths
    # ------------------------------------------------------------------

    def paths(self) -> list[str]:
        """Return a copy of the current watch-folder list."""
        return list(self._paths)

    def set_paths(self, paths: Iterable[str]) -> None:
        """Replace the watch-folder list silently (no signal)."""
        self._paths = [p for p in dict.fromkeys(paths) if p]
        self._repaint_table()

    # ------------------------------------------------------------------
    # Host-facing API - other watcher settings
    # ------------------------------------------------------------------

    def include_sub_dir(self) -> bool:
        return self.chk_sub_dir.isChecked()

    def set_include_sub_dir(self, value: bool) -> None:
        self.chk_sub_dir.blockSignals(True)
        self.chk_sub_dir.setChecked(bool(value))
        self.chk_sub_dir.blockSignals(False)

    def filters(self) -> list[str]:
        """Return the filter list as the host expects it.

        An all-checked state is collapsed to ``[]`` (SDK "all types"
        default) so JSON round-trips stay stable.
        """
        checked = [v for v, c in self._filter_checks.items() if c.isChecked()]
        if len(checked) == len(self._filter_checks):
            return []
        return checked

    def set_filters(self, filters: Iterable[str] | None) -> None:
        """Seed the filter checkboxes. Empty/None means "all types"."""
        cfg = set(filters or [])
        for value, chk in self._filter_checks.items():
            chk.blockSignals(True)
            chk.setChecked(value in cfg if cfg else True)
            chk.blockSignals(False)

    # ------------------------------------------------------------------
    # Host-facing API - UI state
    # ------------------------------------------------------------------

    def add_header_action(self, widget: QWidget) -> None:
        """Place *widget* in the header row (right-aligned area)."""
        self._header_actions.addWidget(widget)

    def set_editable(self, editable: bool) -> None:
        """Enable/disable inputs while the watcher is running."""
        self.btn_add.setEnabled(editable)
        self.chk_sub_dir.setEnabled(editable)
        for chk in self._filter_checks.values():
            chk.setEnabled(editable)
        # Keep the "Remove" buttons in sync with `editable` too.
        for row in range(self.table.rowCount()):
            btn = self.table.cellWidget(row, 1)
            if btn is not None:
                btn.setEnabled(editable)

    def set_refresh_enabled(self, enabled: bool) -> None:
        """Enable the built-in Refresh button (disabled by default)."""
        self.btn_refresh.setEnabled(enabled)

    def set_status_text(self, text: str) -> None:
        """Update the status label in the header (hidden when empty)."""
        self._status.setText(text or '')
        self._status.setVisible(bool(text))

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _on_add_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, 'Select Watch Directory')
        if not path:
            return
        if path in self._paths:
            return
        self._paths.append(path)
        self._repaint_table()
        self.paths_changed.emit(list(self._paths))

    def _on_remove(self, path: str) -> None:
        if path in self._paths:
            self._paths.remove(path)
            self._repaint_table()
            self.paths_changed.emit(list(self._paths))

    def _repaint_table(self) -> None:
        self.table.setRowCount(0)
        for p in self._paths:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(p))
            btn = QPushButton('Remove')
            btn.setProperty('ev_role', 'ghost')
            btn.clicked.connect(lambda _=False, pp=p: self._on_remove(pp))
            self.table.setCellWidget(row, 1, btn)
