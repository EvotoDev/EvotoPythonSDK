"""Module overview page: title, description, member list, and Open Demo button."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QSizePolicy,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont, QCursor


class ClickableMethodLabel(QLabel):
    """Single-line method entry: name in blue, brief in gray.

    When ``clickable`` is False the row renders with plain cursor / no hover
    and swallows clicks - useful for descriptive "highlight" bullets that
    don't have a detail page to navigate to (tool bundles).
    """
    clicked = Signal(int)

    def __init__(
        self,
        name: str,
        brief: str,
        index: int,
        parent=None,
        *,
        clickable: bool = True,
    ):
        super().__init__(parent)
        self._index = index
        self._clickable = clickable
        name_color = "#5da2ff" if clickable else "rgba(243,240,232,0.92)"
        if clickable:
            self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setText(
            f'<span style="color:{name_color};">\u2022 {name}</span>'
            f'<span style="color:rgba(243,240,232,0.64);"> \u2014 {brief}</span>'
        )
        hover = "QLabel:hover { background: rgba(255,255,255,0.06); }" if clickable else ""
        self.setStyleSheet(
            "QLabel { font-size: 12px; padding: 6px 8px; border-radius: 6px;"
            " background: transparent; }" + hover
        )
        self.setWordWrap(True)

    def mousePressEvent(self, ev):
        if self._clickable:
            self.clicked.emit(self._index)


class OverviewPage(QWidget):
    method_clicked = Signal(str, int)
    open_demo_clicked = Signal(str)

    def __init__(self, *, show_demo_btn: bool = False, parent=None):
        super().__init__(parent)
        self._current_module = None
        self._current_data = None
        self._show_demo_btn = show_demo_btn
        self._method_labels: list[ClickableMethodLabel] = []
        self._init_ui()

    def _init_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        self._layout = QVBoxLayout(container)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(12)

        title_row = QHBoxLayout()
        title_row.setSpacing(12)

        title_left = QVBoxLayout()
        title_left.setSpacing(4)
        self._title = QLabel()
        self._title.setObjectName("overviewTitle")
        self._title.setWordWrap(True)
        self._title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._title.setMinimumWidth(100)
        title_left.addWidget(self._title)

        self._subtitle = QLabel()
        self._subtitle.setObjectName("overviewSubtitle")
        self._subtitle.setWordWrap(True)
        title_left.addWidget(self._subtitle)
        title_row.addLayout(title_left, 1)

        if self._show_demo_btn:
            self._demo_btn = QPushButton("Open Demo")
            self._demo_btn.setObjectName("openDemoBtn")
            self._demo_btn.setCursor(QCursor(Qt.PointingHandCursor))
            self._demo_btn.clicked.connect(self._on_demo_click)
            title_row.addWidget(self._demo_btn, 0, Qt.AlignTop)

        self._layout.addLayout(title_row)

        self._import_label = QLabel()
        self._import_label.setObjectName("importPathLabel")
        self._layout.addWidget(self._import_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: rgba(255,255,255,0.06); max-height: 1px;")
        self._layout.addWidget(sep)

        self._members_label = QLabel("List of All Members")
        self._members_label.setObjectName("membersHeader")
        self._layout.addWidget(self._members_label)

        self._methods_list = QVBoxLayout()
        self._methods_list.setSpacing(0)
        self._methods_list.setContentsMargins(0, 0, 0, 0)
        self._layout.addLayout(self._methods_list)

        self._layout.addStretch()

        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def load_module(self, module_key: str, data: dict):
        self._current_module = module_key
        self._current_data = data

        self._title.setText(data["title"])
        self._subtitle.setText(data["subtitle"])
        self._import_label.setText(data["import_path"])

        for lbl in self._method_labels:
            self._methods_list.removeWidget(lbl)
            lbl.deleteLater()
        self._method_labels.clear()

        methods = data.get("methods", [])
        # Tool bundles expose a curated "Highlights" list instead of an API
        # surface - mirror that via ``members_clickable`` / ``members_heading``.
        clickable = data.get("members_clickable", True)
        self._members_label.setText(data.get("members_heading", "List of All Members"))
        self._members_label.setVisible(bool(methods))

        for i, method in enumerate(methods):
            name = method["name"]
            kind = method.get("kind", "method")
            # Only callables get the ``(...)`` suffix - enums, dataclasses,
            # and class summaries are not invoked.
            if (
                clickable
                and kind == "method"
                and (len(method.get("params", [])) > 0 or "(" in name)
            ):
                name = f"{name}(...)"

            lbl = ClickableMethodLabel(
                name, method["brief"], i, self, clickable=clickable,
            )
            if clickable:
                lbl.clicked.connect(self._on_method_click)
            self._methods_list.addWidget(lbl)
            self._method_labels.append(lbl)

    def _on_method_click(self, index: int):
        if self._current_module:
            self.method_clicked.emit(self._current_module, index)

    def _on_demo_click(self):
        if self._current_module:
            self.open_demo_clicked.emit(self._current_module)
