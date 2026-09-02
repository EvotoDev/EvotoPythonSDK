"""Reusable preset tree widget with Recommended / My Presets tabs."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTreeWidget, QTreeWidgetItem, QButtonGroup, QStackedWidget,
)

import evoto

# Tree items show ``name(id)``, so the bare name is kept in its own role for
# callers that need it verbatim.
_NAME_ROLE = Qt.UserRole + 1


class PresetTreeWidget(QFrame):
    """Panel showing presets grouped by class in a tabbed tree view.

    Args:
        multi_select: If True, allows selecting multiple preset items.
            Defaults to False (single selection).
        parent: Parent widget.

    Signals:
        log(str): log messages.
        selection_changed(): fired when preset selection changes.
    """

    log = Signal(str)
    selection_changed = Signal()

    def __init__(self, *, multi_select: bool = False, parent=None):
        super().__init__(parent)
        self._multi_select = multi_select
        self._classes: list = []
        self.setObjectName('panelCard')
        self.setFrameShape(QFrame.StyledPanel)

        inner = QVBoxLayout(self)
        inner.setContentsMargins(12, 10, 12, 12)
        inner.setSpacing(8)

        head = QHBoxLayout()
        title = QLabel('PRESETS')
        title.setProperty('ev_role', 'section-title')
        head.addWidget(title)
        head.addStretch()
        self.btn_refresh = QPushButton('Refresh')
        self.btn_refresh.setProperty('ev_role', 'ghost')
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.clicked.connect(self.refresh)
        head.addWidget(self.btn_refresh)
        inner.addLayout(head)

        tab_row = QHBoxLayout()
        tab_row.setSpacing(6)
        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)
        self.btn_tab_recommended = QPushButton('Recommended')
        self.btn_tab_recommended.setObjectName('taskSegBtn')
        self.btn_tab_recommended.setCheckable(True)
        self.btn_tab_recommended.setChecked(True)
        self.btn_tab_my = QPushButton('My Presets')
        self.btn_tab_my.setObjectName('taskSegBtn')
        self.btn_tab_my.setCheckable(True)
        self._tab_group.addButton(self.btn_tab_recommended, 0)
        self._tab_group.addButton(self.btn_tab_my, 1)
        self._tab_group.buttonClicked.connect(
            lambda btn: self._stack.setCurrentIndex(0 if btn is self.btn_tab_recommended else 1))
        tab_row.addWidget(self.btn_tab_recommended)
        tab_row.addWidget(self.btn_tab_my)
        tab_row.addStretch()
        inner.addLayout(tab_row)

        sel_mode = QTreeWidget.MultiSelection if multi_select else QTreeWidget.SingleSelection
        self.tree_recommended = self._make_tree(sel_mode)
        self.tree_my = self._make_tree(sel_mode)

        self._stack = QStackedWidget()
        self._stack.addWidget(self.tree_recommended)
        self._stack.addWidget(self.tree_my)
        inner.addWidget(self._stack, 1)

    def _make_tree(self, selection_mode) -> QTreeWidget:
        tree = QTreeWidget()
        tree.setHeaderHidden(True)
        tree.setIndentation(20)
        tree.setRootIsDecorated(False)
        tree.setFocusPolicy(Qt.NoFocus)
        tree.setSelectionMode(selection_mode)
        tree.itemClicked.connect(self._on_item_clicked)
        tree.itemSelectionChanged.connect(self.selection_changed.emit)
        return tree

    def _on_item_clicked(self, item: QTreeWidgetItem, _col: int):
        if item.childCount() > 0:
            item.setExpanded(not item.isExpanded())
            item.treeWidget().clearSelection()

    def set_enabled(self, enabled: bool):
        self.btn_refresh.setEnabled(enabled)

    def current_tree(self) -> QTreeWidget:
        return self._stack.currentWidget()

    def selected_preset_ids(self) -> list[str]:
        """Return suit IDs of all selected preset items (leaves only)."""
        ids = []
        for tree in (self.tree_recommended, self.tree_my):
            for item in tree.selectedItems():
                sid = item.data(0, Qt.UserRole)
                if sid is not None:
                    ids.append(str(sid))
        return ids

    def selected_preset_names(self) -> list[str]:
        """Return names of all selected preset items, without the ``(id)`` suffix."""
        names = []
        for tree in (self.tree_recommended, self.tree_my):
            for item in tree.selectedItems():
                if item.data(0, Qt.UserRole) is None:
                    continue
                names.append(item.data(0, _NAME_ROLE) or item.text(0))
        return names

    def _populate_tree(self, tree: QTreeWidget, classes: list) -> int:
        tree.clear()
        total = 0
        for cls in classes:
            class_name = cls.get('name', 'unnamed')
            presets = cls.get('presets', [])
            cat = QTreeWidgetItem(tree)
            cat.setText(0, f'{class_name}  ({len(presets)})')
            cat.setFlags(cat.flags() & ~Qt.ItemIsSelectable)
            for p in presets:
                name = p.get('name', 'unnamed')
                suit_id = p.get('id', '')
                child = QTreeWidgetItem(cat)
                child.setText(0, f'{name}({suit_id})')
                child.setToolTip(0, f'{name}\nid: {suit_id}')
                child.setData(0, Qt.UserRole, suit_id)
                child.setData(0, _NAME_ROLE, name)
                total += 1
        return total

    def refresh(self):
        self.log.emit('Loading presets...')
        try:
            self._classes = evoto.preset.list()
            recommended = [c for c in self._classes if c.get('type') == 'system']
            my_presets = [c for c in self._classes if c.get('type') in ('user', 'team')]
            n1 = self._populate_tree(self.tree_recommended, recommended)
            n2 = self._populate_tree(self.tree_my, my_presets)
            self.log.emit(f'Loaded {len(self._classes)} classes: Recommended {n1}, My Presets {n2}')
        except Exception as exc:
            self.log.emit(f'Failed to load presets: {exc}')
