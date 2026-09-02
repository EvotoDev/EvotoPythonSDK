"""Left-side navigation matching the HTML prototype's three-tier layout.

Structure:
  GUIDES                     (section label)
    Overview                  (nav item - bold)
    Demo Workflow             (nav item - bold)
      PROJECT                 (sub-group label)
        Project               (capability item)
      EXPORT                  (sub-group label)
        Export                (capability item)
        Export Options        (capability item)
      ...
  TOOL BUNDLES               (section label)
    Hot Folder Tool           (nav item - bold)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QCursor


class _SectionLabel(QLabel):
    """Top-level section header (e.g. GUIDES, TOOL BUNDLES)."""

    def __init__(self, text: str, parent=None):
        super().__init__(text.upper(), parent)
        self.setStyleSheet(
            "padding: 14px 14px 4px 14px;"
            " font-size: 10px;"
            " font-weight: 700;"
            " letter-spacing: 1px;"
            " color: rgba(243,240,232,0.55);"
            " background: transparent;"
        )


class _NavItem(QLabel):
    """Bold clickable item (Overview, Demo Workflow, Hot Folder Tool)."""
    clicked = Signal(str)

    def __init__(self, text: str, key: str, parent=None):
        super().__init__(text, parent)
        self._key = key
        self._selected = False
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet(self._make_ss(False))

    def set_selected(self, sel: bool):
        self._selected = sel
        self.setStyleSheet(self._make_ss(sel))

    def mousePressEvent(self, ev):
        ev.accept()
        real_pos = self.mapFromGlobal(QCursor.pos())
        if not self.rect().contains(real_pos):
            return
        self.clicked.emit(self._key)

    @staticmethod
    def _make_ss(selected: bool) -> str:
        base = (
            "padding: 7px 12px;"
            " border: 1px solid transparent;"
            " border-radius: 6px;"
            " margin: 1px 6px;"
            " font-size: 12px;"
            " font-weight: 600;"
        )
        if selected:
            return (
                f"QLabel {{ {base}"
                " background: rgba(255,255,255,0.08);"
                " border-color: rgba(255,255,255,0.08);"
                " color: #f3f0e8; }"
            )
        return (
            f"QLabel {{ {base}"
            " background: transparent;"
            " color: rgba(243,240,232,0.78); }"
            " QLabel:hover { background: rgba(255,255,255,0.06); }"
        )


class _GroupLabel(QLabel):
    """Sub-group header inside Demo Workflow (e.g. PROJECT, EXPORT)."""

    def __init__(self, text: str, parent=None):
        super().__init__(text.upper(), parent)
        self.setStyleSheet(
            "padding: 10px 14px 2px 18px;"
            " font-size: 10px;"
            " font-weight: 700;"
            " letter-spacing: 1px;"
            " color: rgba(243,240,232,0.55);"
            " background: transparent;"
        )


class _CapabilityItem(QLabel):
    """Clickable capability item under a sub-group."""
    clicked = Signal(str)

    def __init__(self, text: str, key: str, parent=None):
        super().__init__(text, parent)
        self._key = key
        self._selected = False
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet(self._make_ss(False))

    def set_selected(self, sel: bool):
        self._selected = sel
        self.setStyleSheet(self._make_ss(sel))

    def mousePressEvent(self, ev):
        ev.accept()
        real_pos = self.mapFromGlobal(QCursor.pos())
        if not self.rect().contains(real_pos):
            return
        self.clicked.emit(self._key)

    @staticmethod
    def _make_ss(selected: bool) -> str:
        base = (
            "padding: 6px 12px 6px 22px;"
            " border: 1px solid transparent;"
            " border-radius: 6px;"
            " margin: 1px 6px;"
            " font-size: 12px;"
        )
        if selected:
            return (
                f"QLabel {{ {base}"
                " background: rgba(255,255,255,0.08);"
                " border-color: rgba(255,255,255,0.08);"
                " color: #f3f0e8; }"
            )
        return (
            f"QLabel {{ {base}"
            " background: transparent;"
            " color: rgba(243,240,232,0.64); }"
            " QLabel:hover { background: rgba(255,255,255,0.06); }"
        )


class Sidebar(QWidget):
    module_selected = Signal(str)

    def __init__(self, workflow_groups: list, display_names: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self._workflow_groups = workflow_groups
        self._display_names = display_names
        self._all_selectables: list[_NavItem | _CapabilityItem] = []
        self._key_map: dict[str, _NavItem | _CapabilityItem] = {}
        self._subtree: QWidget | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("Evoto Plugin SDK")
        title.setObjectName("sidebarTitle")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        nav = QVBoxLayout(container)
        nav.setContentsMargins(4, 4, 4, 8)
        nav.setSpacing(0)

        # ── GUIDES section ──
        nav.addWidget(_SectionLabel("Guides"))

        overview = _NavItem("Overview", "__overview__")
        overview.clicked.connect(self._on_select)
        nav.addWidget(overview)
        self._all_selectables.append(overview)
        self._key_map["__overview__"] = overview

        demo_wf = _NavItem("Demo Workflow", "__demo_workflow__")
        demo_wf.clicked.connect(self._on_select)
        nav.addWidget(demo_wf)
        self._all_selectables.append(demo_wf)
        self._key_map["__demo_workflow__"] = demo_wf

        # Capability sub-tree (inside Demo Workflow)
        subtree = QWidget()
        subtree_layout = QVBoxLayout(subtree)
        subtree_layout.setContentsMargins(0, 0, 0, 0)
        subtree_layout.setSpacing(0)

        for group in self._workflow_groups:
            if "label" in group and len(group["items"]) > 1:
                subtree_layout.addWidget(_GroupLabel(group["label"]))
            for key in group["items"]:
                name = self._display_names.get(key, key)
                item = _CapabilityItem(name, key)
                item.clicked.connect(self._on_select)
                subtree_layout.addWidget(item)
                self._all_selectables.append(item)
                self._key_map[key] = item

        self._subtree = subtree
        nav.addWidget(subtree)

        # ── TOOL BUNDLES section ──
        nav.addWidget(_SectionLabel("Tool Bundles"))

        hot_folder = _NavItem("Hot Folder Tool", "__hot_folder__")
        hot_folder.clicked.connect(self._on_select)
        nav.addWidget(hot_folder)
        self._all_selectables.append(hot_folder)
        self._key_map["__hot_folder__"] = hot_folder

        nav.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _on_select(self, key: str):
        for item in self._all_selectables:
            item.set_selected(item._key == key)
        self.module_selected.emit(key)

    def select_module(self, module_key: str):
        item = self._key_map.get(module_key)
        if item:
            self._on_select(module_key)
