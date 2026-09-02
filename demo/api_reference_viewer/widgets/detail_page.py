"""API detail page - Qt-doc style single-column flow.

Layout (top to bottom):
    Back + title + brief
    Section: Synopsis      -> signature (code block)
    Section: Parameters    -> stacked per-parameter rows
    Section: Returns       -> block with return type + description
    Section: Example       -> code block

Visual rules follow ``plan/EVOTO_PLUGIN_SDK_POPUP_VISUAL_RULES.md`` strictly:
  - Module panel: #232629 + 1px rgba(255,255,255,0.07) + r8
  - Content block: #0000004d + 1px rgba(255,255,255,0.05) + r6
  - Module title sits at the top, inside the panel
  - API-member links inside docs use #5da2ff
"""

import re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QScrollArea, QFrame, QSizePolicy,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont, QCursor, QTextOption


_IDENT_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")


def _linkify_types(
    text: str, type_index: dict[str, tuple[str, int]] | None
) -> str:
    """Wrap occurrences of known type names in clickable HTML anchors.

    The href encodes ``module_key|index`` and is parsed back out by the
    detail page click handler. Non-matching tokens stay verbatim. HTML
    metacharacters around the matched tokens are escaped so the output
    is safe for ``QLabel.setText`` in rich-text mode.
    """
    if not text:
        return ""
    if not type_index:
        return _html_escape(text)

    out: list[str] = []
    pos = 0
    for match in _IDENT_RE.finditer(text):
        # Escape any literal text since the previous match boundary.
        out.append(_html_escape(text[pos : match.start()]))
        token = match.group(1)
        if token in type_index:
            module_key, idx = type_index[token]
            href = f"type:{module_key}|{idx}"
            out.append(f'<a href="{href}">{_html_escape(token)}</a>')
        else:
            out.append(_html_escape(token))
        pos = match.end()
    out.append(_html_escape(text[pos:]))
    return "".join(out)


def _html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _make_section(title: str, subtitle: str = "") -> tuple:
    """Create a panel-styled section box.

    Returns ``(panel, body_layout, title_lbl, subtitle_lbl)`` so callers
    can update the section labels at runtime (e.g. swap "Parameters" for
    "Members" on enum entries).
    """
    panel = QFrame()
    panel.setObjectName("docSection")

    layout = QVBoxLayout(panel)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(8)

    title_lbl = QLabel(title)
    title_lbl.setObjectName("docSectionTitle")
    layout.addWidget(title_lbl)

    sub_lbl = QLabel(subtitle)
    sub_lbl.setObjectName("docSectionSubtitle")
    sub_lbl.setWordWrap(True)
    sub_lbl.setVisible(bool(subtitle))
    layout.addWidget(sub_lbl)

    body = QVBoxLayout()
    body.setContentsMargins(0, 0, 0, 0)
    body.setSpacing(6)
    layout.addLayout(body)

    return panel, body, title_lbl, sub_lbl


class _ParamRow(QFrame):
    """Single parameter entry styled as an inner content block.

    The ``type`` and ``default`` fields render as rich text so any token
    matching a known type name (passed via ``type_index``) becomes a
    clickable link. Activating a link emits :attr:`type_link_clicked`.
    """

    type_link_clicked = Signal(str, int)

    def __init__(
        self,
        name: str,
        ptype: str,
        default: str,
        desc: str,
        parent=None,
        *,
        type_index: dict[str, tuple[str, int]] | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("docBlock")
        self._type_index = type_index or {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(8)
        header.setContentsMargins(0, 0, 0, 0)

        name_lbl = QLabel(name)
        name_lbl.setObjectName("paramName")
        header.addWidget(name_lbl)

        if ptype:
            type_lbl = QLabel()
            type_lbl.setObjectName("paramType")
            type_lbl.setTextFormat(Qt.RichText)
            type_lbl.setText(": " + _linkify_types(ptype, self._type_index))
            type_lbl.setOpenExternalLinks(False)
            type_lbl.linkActivated.connect(self._on_link)
            type_lbl.setTextInteractionFlags(
                Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse
            )
            header.addWidget(type_lbl)

        header.addStretch(1)

        if default:
            is_required = default.strip().lower() == "required"
            default_lbl = QLabel()
            default_lbl.setObjectName(
                "paramDefaultRequired" if is_required else "paramDefault"
            )
            default_lbl.setTextFormat(Qt.RichText)
            if is_required:
                default_lbl.setText("required")
            else:
                default_lbl.setText("= " + _linkify_types(default, self._type_index))
            default_lbl.setOpenExternalLinks(False)
            default_lbl.linkActivated.connect(self._on_link)
            default_lbl.setTextInteractionFlags(
                Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse
            )
            header.addWidget(default_lbl, 0, Qt.AlignRight)

        outer.addLayout(header)

        if desc:
            desc_lbl = QLabel(desc)
            desc_lbl.setObjectName("paramDesc")
            desc_lbl.setWordWrap(True)
            desc_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            outer.addWidget(desc_lbl)

    def _on_link(self, href: str):
        if not href.startswith("type:"):
            return
        try:
            payload = href[len("type:") :]
            module_key, idx = payload.rsplit("|", 1)
            self.type_link_clicked.emit(module_key, int(idx))
        except (ValueError, IndexError):
            return


class DetailPage(QWidget):
    back_clicked = Signal()
    #: Emitted when the user clicks a type-name link inside a parameter
    #: row. Carries ``(module_key, method_index)`` so the host window can
    #: navigate to the matching detail entry.
    type_link_clicked = Signal(str, int)

    def __init__(
        self,
        parent=None,
        *,
        type_index: dict[str, tuple[str, int]] | None = None,
    ):
        super().__init__(parent)
        self._type_index = type_index or {}
        self._init_ui()

    def _init_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ── Header: back + title + brief ──
        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        title_row.setContentsMargins(0, 0, 0, 0)

        back_btn = QPushButton("\u2190")
        back_btn.setObjectName("backBtn")
        back_btn.setFixedSize(28, 28)
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.clicked.connect(self.back_clicked.emit)
        title_row.addWidget(back_btn, 0, Qt.AlignTop)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        self._title = QLabel()
        self._title.setObjectName("detailTitle")
        self._title.setWordWrap(True)
        self._title.setTextInteractionFlags(Qt.TextSelectableByMouse)
        title_col.addWidget(self._title)

        self._subtitle = QLabel()
        self._subtitle.setObjectName("detailSubtitle")
        self._subtitle.setWordWrap(True)
        self._subtitle.setTextInteractionFlags(Qt.TextSelectableByMouse)
        title_col.addWidget(self._subtitle)
        title_row.addLayout(title_col, 1)

        root.addLayout(title_row)

        # ── Synopsis section ──
        syn_panel, syn_body, self._syn_title, self._syn_sub = _make_section(
            "Synopsis", "Method shape, including parameters and return type."
        )
        self._signature = QTextEdit()
        self._signature.setObjectName("codeBlock")
        self._signature.setReadOnly(True)
        mono = QFont("SF Mono", 12)
        mono.setStyleHint(QFont.Monospace)
        self._signature.setFont(mono)
        # Wrap long signatures at the widget edge and auto-grow vertically
        # so users never need to side-scroll to read the parameter list or
        # the return type.
        self._signature.setLineWrapMode(QTextEdit.WidgetWidth)
        self._signature.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self._signature.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._signature.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._signature.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self._signature.document().contentsChanged.connect(
            self._resize_signature
        )
        syn_body.addWidget(self._signature)
        root.addWidget(syn_panel)

        # ── Parameters section ──
        (
            self._params_panel,
            self._params_body,
            self._params_title,
            self._params_sub,
        ) = _make_section(
            "Parameters", "Details of each accepted argument."
        )
        root.addWidget(self._params_panel)

        # ── Returns section ──
        (
            self._returns_panel,
            self._returns_body,
            self._returns_title,
            self._returns_sub,
        ) = _make_section(
            "Returns", "What the callable produces on success."
        )
        self._returns_block = QFrame()
        self._returns_block.setObjectName("docBlock")
        returns_layout = QVBoxLayout(self._returns_block)
        returns_layout.setContentsMargins(10, 8, 10, 8)
        returns_layout.setSpacing(0)
        self._returns_text = QLabel()
        self._returns_text.setObjectName("returnsText")
        self._returns_text.setWordWrap(True)
        self._returns_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        returns_layout.addWidget(self._returns_text)
        self._returns_body.addWidget(self._returns_block)
        root.addWidget(self._returns_panel)

        # ── Example section ──
        (
            self._example_panel,
            example_body,
            self._example_title,
            self._example_sub,
        ) = _make_section(
            "Example", "Reference invocation for the selected capability."
        )
        self._code = QTextEdit()
        self._code.setObjectName("codeBlock")
        self._code.setReadOnly(True)
        self._code.setFont(mono)
        self._code.setMinimumHeight(140)
        example_body.addWidget(self._code)
        root.addWidget(self._example_panel)

        root.addStretch(1)

        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _resize_signature(self):
        """Match the synopsis box height to its wrapped content.

        Without this the box uses the wrap width but a fixed visual
        height, so multi-line signatures get cut off / scrolled.
        """
        doc = self._signature.document()
        margins = self._signature.contentsMargins()
        # ``QTextDocument.size()`` already accounts for line wrapping at
        # the widget's current width.
        doc_height = doc.size().height()
        frame = 2 * self._signature.frameWidth()
        self._signature.setFixedHeight(
            int(doc_height) + margins.top() + margins.bottom() + frame + 4
        )

    def _clear_params(self):
        while self._params_body.count():
            item = self._params_body.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def load_method(self, method: dict):
        self._title.setText(method["name"])
        brief = method.get("brief", "")
        self._subtitle.setText(brief)
        self._subtitle.setVisible(bool(brief))

        self._signature.setPlainText(method.get("signature", ""))

        kind = method.get("kind", "method")
        # Section labels track whether the entry is a method, an enum, a
        # dataclass, or a class summary - the data is the same shape but
        # the meaning differs and the labels should reflect that.
        if kind == "enum":
            self._syn_title.setText("Definition")
            self._syn_sub.setText("Enum class declaration.")
            self._params_title.setText("Members")
            self._params_sub.setText("Allowed values for this enum.")
            self._params_sub.setVisible(True)
            empty_text = "No members."
        elif kind == "dataclass":
            self._syn_title.setText("Definition")
            self._syn_sub.setText("Dataclass declaration.")
            self._params_title.setText("Fields")
            self._params_sub.setText("Each attribute on the dataclass.")
            self._params_sub.setVisible(True)
            empty_text = "No fields."
        elif kind == "class":
            self._syn_title.setText("Definition")
            self._syn_sub.setText("Class declaration.")
            self._params_title.setText("Members")
            self._params_sub.setText("Public attributes / nested types.")
            self._params_sub.setVisible(True)
            empty_text = "No members."
        else:
            self._syn_title.setText("Synopsis")
            self._syn_sub.setText(
                "Method shape, including parameters and return type."
            )
            self._params_title.setText("Parameters")
            self._params_sub.setText("Details of each accepted argument.")
            self._params_sub.setVisible(True)
            empty_text = "No parameters."

        params = method.get("params", [])
        self._clear_params()
        if params:
            for name, ptype, default, desc in params:
                row = _ParamRow(
                    name,
                    ptype,
                    default,
                    desc,
                    type_index=self._type_index,
                )
                row.type_link_clicked.connect(self.type_link_clicked.emit)
                self._params_body.addWidget(row)
            self._params_panel.setVisible(True)
        else:
            empty = QLabel(empty_text)
            empty.setObjectName("paramDesc")
            self._params_body.addWidget(empty)
            self._params_panel.setVisible(True)

        # Returns section is only meaningful for methods. Hide it for
        # enums / dataclasses / classes whose "value" is structural.
        if kind == "method":
            returns = method.get("returns", "")
            if returns:
                self._returns_text.setText(returns)
                self._returns_panel.setVisible(True)
            else:
                self._returns_panel.setVisible(False)
        else:
            self._returns_panel.setVisible(False)

        example = method.get("example", "")
        self._code.setPlainText(example)
        self._example_panel.setVisible(bool(example))
