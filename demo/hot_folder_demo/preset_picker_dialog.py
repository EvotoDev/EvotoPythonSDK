"""Modal dialog that picks one or more preset suits.

Wraps :class:`demo.shared.preset_tree.PresetTreeWidget` in multi-select
mode so each mapping row can bind to multiple preset suits - the lane
then exports every incoming image under *every* selected suit, one
``export.start_with_custom`` call per lane with the full list passed in.
"""

from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QTreeWidget, QVBoxLayout,
)

from demo.shared import PresetTreeWidget, apply_theme, themed_message


class PresetPickerDialog(QDialog):
    """Pick one or more preset suits for a mapping row.

    Returns ``(ids, names)`` as parallel lists on accept, ``None`` on
    cancel. When ``current_ids`` is passed, matching items are
    pre-selected after the tree loads so the dialog re-opens in the
    same state the user left it in.
    """

    def __init__(
        self,
        *,
        current_ids: Iterable[str] = (),
        parent=None,
    ):
        super().__init__(parent)
        self._current_ids = [str(x) for x in current_ids if x]
        self._result: tuple[list[str], list[str]] | None = None

        self.setWindowTitle('Pick Preset Suit(s)')
        self.setModal(True)
        self.resize(520, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        hint = QLabel(
            'Choose one or more preset suits. Every image in this lane '
            'will be exported under each selected suit.')
        hint.setWordWrap(True)
        hint.setProperty('ev_role', 'section-caption')
        root.addWidget(hint)

        self.preset_tree = PresetTreeWidget(multi_select=True)
        self.preset_tree.set_enabled(True)
        root.addWidget(self.preset_tree, 1)

        self.btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        self.btns.accepted.connect(self._on_accept)
        self.btns.rejected.connect(self.reject)
        self.btns.button(QDialogButtonBox.Ok).setProperty('ev_role', 'primary')
        root.addWidget(self.btns)

        apply_theme(self)
        self.preset_tree.refresh()
        # Preselect after refresh so saved IDs survive a dialog reopen.
        self._apply_preselection()

    # ------------------------------------------------------------------

    def _apply_preselection(self) -> None:
        if not self._current_ids:
            return
        wanted = set(self._current_ids)
        for tree in (self.preset_tree.tree_recommended,
                     self.preset_tree.tree_my):
            self._select_matching(tree, wanted)

    @staticmethod
    def _select_matching(tree: QTreeWidget, wanted: set[str]) -> None:
        # Each top-level item is a preset class; leaves carry the suit
        # id in ``Qt.UserRole``. Expanding the parent on match keeps the
        # selection visible without forcing the whole tree open.
        for i in range(tree.topLevelItemCount()):
            parent = tree.topLevelItem(i)
            for j in range(parent.childCount()):
                child = parent.child(j)
                sid = child.data(0, Qt.UserRole)
                if sid is not None and str(sid) in wanted:
                    child.setSelected(True)
                    parent.setExpanded(True)

    def _on_accept(self) -> None:
        ids = self.preset_tree.selected_preset_ids()
        names = self.preset_tree.selected_preset_names()
        if not ids:
            themed_message(
                self, 'No Selection', 'Pick at least one preset suit.')
            return
        # Ensure parallel lists stay the same length even if a name
        # somehow dropped out of the selection callback ordering.
        if len(names) < len(ids):
            names = names + [ids[i] for i in range(len(names), len(ids))]
        self._result = (list(ids), list(names))
        self.accept()

    def selection(self) -> tuple[list[str], list[str]] | None:
        return self._result
