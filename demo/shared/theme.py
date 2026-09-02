"""Shared dark theme QSS for all demos."""

from pathlib import Path

from PySide6.QtWidgets import QSizePolicy

_TICK_SVG = str(Path(__file__).resolve().parent / 'tick.svg').replace('\\', '/')
_CARET_SVG = str(Path(__file__).resolve().parent / 'caret.svg').replace('\\', '/')

# Interpolated into the QCheckBox rules below and reused by
# fix_checkbox_width(), which has to reproduce the indicator geometry to
# compute a label-safe minimum width.
_CHECKBOX_INDICATOR_PX = 16
_CHECKBOX_SPACING_PX = 6

DARK_QSS = f"""
QWidget {{
    background: #16181a;
    color: #f3f0e8;
    font-size: 12px;
}}
QLabel {{
    color: rgba(243, 240, 232, 0.78);
    background: transparent;
}}
QLabel[ev_role="section-title"] {{
    color: #f3f0e8; font-weight: 700; font-size: 11px;
    letter-spacing: 0.06em; background: transparent;
}}
QLabel[ev_role="section-caption"] {{
    color: rgba(243, 240, 232, 0.50);
    font-size: 11px; background: transparent;
}}
QLabel[ev_role="field-label"] {{
    color: rgba(243, 240, 232, 0.50);
    font-size: 10px; background: transparent;
}}
QLabel[ev_role="status-disconnected"],
QLabel[ev_role="status-connecting"],
QLabel[ev_role="status-connected"] {{
    padding: 5px 10px; border-radius: 999px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.05);
    font-weight: 700;
}}
QLabel[ev_role="status-disconnected"] {{ color: #ef8f8f; }}
QLabel[ev_role="status-connecting"]   {{ color: #f0c548; }}
QLabel[ev_role="status-connected"]    {{ color: #8fd7a7; }}
QLabel[ev_role="done"] {{
    color: #8fd7a7; font-weight: 700; background: transparent;
}}
QLabel[ev_role="env-badge-nonprod"] {{
    padding: 3px 8px; border-radius: 4px;
    background: rgba(240, 197, 72, 0.18);
    border: 1px solid rgba(240, 197, 72, 0.45);
    color: #f0c548; font-weight: 700; font-size: 10px;
    letter-spacing: 0.04em;
}}
QCheckBox {{
    color: rgba(243, 240, 232, 0.88);
    spacing: {_CHECKBOX_SPACING_PX}px;
    background: transparent;
}}
QCheckBox::indicator {{
    min-width: {_CHECKBOX_INDICATOR_PX}px; max-width: {_CHECKBOX_INDICATOR_PX}px;
    min-height: {_CHECKBOX_INDICATOR_PX}px; max-height: {_CHECKBOX_INDICATOR_PX}px;
    border-radius: 2px;
    border: 1px solid #9c9d9f;
    background: rgba(255, 255, 255, 0.02);
}}
QCheckBox::indicator:hover {{
    border: 1px solid #3083ff; background: rgba(48, 131, 255, 0.10);
}}
QCheckBox::indicator:checked {{
    border: none; background: #3083ff;
    image: url({_TICK_SVG});
}}
QCheckBox::indicator:checked:hover {{ background: rgba(48, 131, 255, 0.55); }}
QCheckBox::indicator:checked:disabled {{ background: rgba(48, 131, 255, 0.20); }}
QCheckBox::indicator:disabled {{
    border: 1px solid #444649; background: rgba(255, 255, 255, 0.01);
}}
QGroupBox {{
    background: #232629;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 8px; margin-top: 0; padding-top: 18px;
    font-weight: 600; color: #f3f0e8;
}}
QGroupBox::title {{
    subcontrol-origin: padding; subcontrol-position: top left;
    top: 4px; left: 12px; padding: 0;
    color: #f3f0e8; background: transparent;
}}
QLineEdit, QTextEdit, QListWidget, QComboBox, QSpinBox,
QDoubleSpinBox, QTableWidget {{
    background: #0000004d;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 6px; color: #f3f0e8;
    selection-background-color: rgba(255, 255, 255, 0.10);
    selection-color: #f3f0e8;
}}
QLineEdit, QSpinBox, QDoubleSpinBox {{ min-height: 28px; padding: 0 10px; }}
QComboBox {{ min-height: 28px; padding: 0 26px 0 10px; combobox-popup: 0; }}
QComboBox::drop-down {{
    subcontrol-origin: padding; subcontrol-position: center right;
    border: none; width: 22px; background: transparent;
}}
QComboBox::down-arrow {{
    image: url({_CARET_SVG}); width: 10px; height: 10px;
}}
QComboBox::down-arrow:on {{ top: 1px; }}
QComboBox::down-arrow:disabled {{ image: url({_CARET_SVG}); }}
QComboBox QAbstractItemView {{
    background: #232629;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    color: #f3f0e8;
    padding: 4px;
    outline: 0;
    selection-background-color: rgba(255, 255, 255, 0.10);
    selection-color: #f3f0e8;
}}
QComboBox QAbstractItemView::item {{
    min-height: 26px; padding: 0 8px; border-radius: 4px;
    background: transparent; color: #f3f0e8;
}}
QComboBox QAbstractItemView::item:selected,
QComboBox QAbstractItemView::item:hover {{
    background: rgba(255, 255, 255, 0.08); color: #f3f0e8;
}}
QTextEdit, QListWidget {{ padding: 8px; }}
QListWidget::item {{
    padding: 6px 8px; border-radius: 4px; background: transparent;
}}
QListWidget::item:selected {{
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.08);
}}
QListWidget::item:hover {{ background: rgba(255, 255, 255, 0.04); }}
QTreeView {{
    background: #0000004d;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 6px; color: #f3f0e8; padding: 4px;
    outline: 0; show-decoration-selected: 0;
    selection-background-color: transparent; selection-color: #f3f0e8;
}}
QTreeView::item {{
    padding: 5px 6px; border-radius: 4px;
    border: none; background: transparent; color: #f3f0e8;
}}
QTreeView::item:selected {{ background: rgba(255, 255, 255, 0.08); color: #f3f0e8; }}
QTreeView::item:hover:!selected {{ background: rgba(255, 255, 255, 0.04); }}
QTreeView::branch {{
    background: transparent; border: none; border-image: none;
    image: none; selection-background-color: transparent;
}}
QTreeView::branch:selected {{ background: transparent; }}
QTreeView::branch:has-children:closed,
QTreeView::branch:has-children:open {{ image: none; }}
QHeaderView::section {{
    background: rgba(255, 255, 255, 0.04);
    color: rgba(243, 240, 232, 0.72);
    border: none; border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    padding: 8px 10px; font-size: 11px; font-weight: 700;
}}
QTableWidget {{ gridline-color: rgba(255, 255, 255, 0.04); }}
QTableWidget::item {{ padding: 6px; background: transparent; }}
QPushButton {{
    min-height: 28px; padding: 0 10px; border-radius: 6px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    background: rgba(255, 255, 255, 0.06);
    color: rgba(243, 240, 232, 0.84);
    font-size: 12px; font-weight: 600;
}}
QPushButton:hover  {{ background: rgba(255, 255, 255, 0.10); }}
QPushButton:pressed {{ background: rgba(255, 255, 255, 0.14); }}
QPushButton:disabled {{
    background: rgba(255, 255, 255, 0.03);
    color: rgba(243, 240, 232, 0.30);
    border-color: rgba(255, 255, 255, 0.04);
}}
QPushButton[ev_role="ghost"] {{
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.05);
    color: rgba(243, 240, 232, 0.72);
}}
QPushButton[ev_role="ghost"]:hover {{ background: rgba(255, 255, 255, 0.08); }}
QPushButton[ev_role="primary"] {{
    background: #f0c548; color: #231a00;
    border: 1px solid rgba(240, 197, 72, 0.45); font-weight: 700;
    border-radius: 14px; padding: 0 16px;
}}
QPushButton[ev_role="primary"]:hover {{ background: #f4cd62; }}
QPushButton[ev_role="primary"]:disabled {{
    background: rgba(240, 197, 72, 0.25); color: rgba(35, 26, 0, 0.5);
}}
QPushButton[ev_role="danger"] {{ color: #ef8f8f; }}
QPushButton#taskSegBtn {{
    padding: 3px 14px; border-radius: 4px;
    border: 1px solid rgba(255, 255, 255, 0.05);
    background: rgba(255, 255, 255, 0.04);
    color: rgba(243, 240, 232, 0.64);
}}
QPushButton#taskSegBtn:checked {{
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #f3f0e8; font-weight: 700;
}}
QFrame#optionCard, QFrame#panelCard, QFrame#summaryChip,
QFrame#workflowFrame, QFrame#exportModeShell {{
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 6px; background-color: #232629;
}}
QFrame#exportModeShell {{ border-radius: 8px; }}
QRadioButton {{
    spacing: 6px; color: rgba(243, 240, 232, 0.88); background: transparent;
}}
QRadioButton::indicator {{
    width: 14px; height: 14px; border: 2px solid #9c9d9f;
    border-radius: 9px; background-color: #232629;
}}
QRadioButton::indicator:checked {{
    border: 2px solid #3083ff; background-color: #3083ff;
}}
QRadioButton::indicator:hover {{ border-color: #6ba3ff; }}
QRadioButton:disabled {{ color: rgba(243, 240, 232, 0.30); }}
QRadioButton::indicator:disabled {{
    border: 2px solid #444649; background-color: rgba(255, 255, 255, 0.01);
}}
QRadioButton::indicator:checked:disabled {{
    border: 2px solid rgba(48, 131, 255, 0.20);
    background-color: rgba(48, 131, 255, 0.20);
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled,
QComboBox:disabled, QTextEdit:disabled {{
    background: rgba(0, 0, 0, 0.15);
    color: rgba(243, 240, 232, 0.30);
    border: 1px solid rgba(255, 255, 255, 0.03);
}}
QSlider::groove:horizontal {{
    height: 4px; background: rgba(255, 255, 255, 0.08); border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 14px; height: 14px; margin: -5px 0;
    background: #c0c0c0; border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: rgba(255, 255, 255, 0.25); border-radius: 2px;
}}
QSlider::handle:horizontal:disabled {{ background: rgba(255, 255, 255, 0.15); }}
QSlider::sub-page:horizontal:disabled {{ background: rgba(255, 255, 255, 0.08); }}
QSlider::groove:horizontal:disabled {{ background: rgba(255, 255, 255, 0.04); }}
QSplitter::handle {{ background: #16181a; }}
QScrollBar:vertical, QScrollBar:horizontal {{
    background: #16181a; border-radius: 4px;
}}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: rgba(255, 255, 255, 0.10); border-radius: 4px;
}}
"""


def apply_theme(widget) -> None:
    """Apply the shared dark theme to a top-level widget."""
    widget.setStyleSheet(DARK_QSS)


def fix_checkbox_width(chk) -> None:
    """Guarantee a checkbox always shows its full label.

    Demos build their widget tree first and apply the QSS afterwards. In that
    order ``QCheckBox.sizeHint()`` under-reports the indicator width - it was
    computed against the pre-QSS style and is never refreshed - so a crowded
    row happily shrinks the checkbox and truncates the label, e.g.
    "auto_load_model" rendering as "auto_load_mo".

    ``QSizePolicy.Fixed`` does not help because it still trusts that stale
    hint, so pin ``minimumWidth`` to a value derived from the current font
    metrics and the indicator geometry declared above, plus a small cushion so
    antialiased glyphs are not clipped.
    """

    text_width = chk.fontMetrics().horizontalAdvance(chk.text())
    padding = 8
    chk.setMinimumWidth(
        text_width + _CHECKBOX_INDICATOR_PX + _CHECKBOX_SPACING_PX + padding
    )
    chk.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
