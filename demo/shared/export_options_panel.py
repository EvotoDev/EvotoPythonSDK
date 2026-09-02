"""Shared Format + Quality panel for custom export flows.

Lifted from ``preset_export_demo`` - two stacked cards ("Format" and
"Quality") that together map to the subset of ``ExportOptions`` that
demos routinely want the user to tweak:

* ``file_format`` (JPG / TIFF 8-bit / TIFF 16-bit / PNG / Original)
* ``quality_type`` + ``quality`` (Percent mode) OR ``limit_size`` (Size mode)

Every other ``ExportOptions`` knob stays on the active preset - the
host applies its own fallbacks for keys the dict does not carry,
which is exactly the behaviour we want for a "tweak a couple of
things" UI.

The panel is layout-only; callers drop it into their own dialog /
workflow card, connect :attr:`options_changed`, and read state through
:meth:`to_options` / :meth:`load_options`.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QFrame, QHBoxLayout, QLabel, QRadioButton,
    QSlider, QSpinBox, QVBoxLayout, QWidget,
)

from evoto.export_options import (
    ExportOptions, FileFormat, QualityType, ScaleType,
)


# Widget defaults - aligned with the host's fallbacks in parseExportOptions.
_DEFAULT_QUALITY_PCT = 80       # demo default; host fallback when unset is 100
_DEFAULT_LIMIT_MB = 10          # matches host fallback
_QUALITY_PRESETS = (            # preset combo: label -> percent value
    ('High',   80),
    ('Medium', 60),
    ('Low',    40),
)
_FORMAT_CHOICES: tuple[tuple[str, str], ...] = (
    ('JPG',            FileFormat.JPEG.value),
    ('TIFF(8 bits)',   FileFormat.TIFF_8BIT.value),
    ('TIFF(16 bits)',  FileFormat.TIFF_16BIT.value),
    ('PNG',            FileFormat.PNG.value),
    ('Original Format', FileFormat.ORIGINAL.value),
)


def _make_card(object_name: str = 'optionCard') -> tuple[QFrame, QVBoxLayout]:
    """Standard "option card" frame - matches the demos' QSS."""
    fr = QFrame()
    fr.setFrameShape(QFrame.StyledPanel)
    fr.setObjectName(object_name)
    lay = QVBoxLayout(fr)
    lay.setContentsMargins(8, 6, 8, 6)
    lay.setSpacing(4)
    return fr, lay


class ExportOptionsPanel(QWidget):
    """Format + Quality editor, reusable across demos.

    Contains two stacked cards. The layout / interlocks match
    ``preset_export_demo`` one-to-one; the panel simply packages them
    as a reusable ``QWidget`` and offers a dict-in / dict-out API.
    """

    options_changed = Signal()

    # ------------------------------------------------------------------

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        root.addWidget(self._build_format_card())
        root.addWidget(self._build_quality_card())

        self._connect_signals()
        self._refresh_interlocks()

    # ------------------------------------------------------------------
    # UI builders
    # ------------------------------------------------------------------

    def _build_format_card(self) -> QFrame:
        card, lay = _make_card()

        row = QHBoxLayout()
        label = QLabel('Format')
        label.setProperty('ev_role', 'field-label')
        label.setFixedWidth(70)
        self.fmt_combo = QComboBox()
        for display, value in _FORMAT_CHOICES:
            self.fmt_combo.addItem(display, value)
        row.addWidget(label)
        row.addWidget(self.fmt_combo, 1)
        lay.addLayout(row)

        return card

    def _build_quality_card(self) -> QFrame:
        card, lay = _make_card()

        title = QLabel('Quality')
        title.setProperty('ev_role', 'field-label')
        lay.addWidget(title)

        # Row 1 - "Limit file size to" radio + MB spin.
        self.quality_group = QButtonGroup(self)
        self.quality_group.setExclusive(True)

        q1 = QHBoxLayout()
        self.radio_quality_size = QRadioButton('Limit file size to')
        self.spin_limit_mb = QSpinBox()
        self.spin_limit_mb.setRange(1, 9999)
        self.spin_limit_mb.setValue(_DEFAULT_LIMIT_MB)
        self.spin_limit_mb.setSuffix(' MB')
        self.spin_limit_mb.setFixedWidth(100)
        self.spin_limit_mb.setEnabled(False)
        q1.addWidget(self.radio_quality_size)
        q1.addStretch()
        q1.addWidget(self.spin_limit_mb)
        lay.addLayout(q1)

        # Row 2 - "Percentage" radio (single-widget row, mirrors
        # preset_export_demo verbatim).
        q2 = QHBoxLayout()
        self.radio_quality_percent = QRadioButton('Percentage')
        self.radio_quality_percent.setChecked(True)
        q2.addWidget(self.radio_quality_percent)
        q2.addStretch()
        lay.addLayout(q2)

        self.quality_group.addButton(self.radio_quality_size, 0)
        self.quality_group.addButton(self.radio_quality_percent, 1)

        # Row 3 - quality preset combo + explicit percent spin.
        q3 = QHBoxLayout()
        self.combo_quality_preset = QComboBox()
        for label, value in _QUALITY_PRESETS:
            self.combo_quality_preset.addItem(label, value)
        self.spin_quality_percent = QSpinBox()
        self.spin_quality_percent.setRange(1, 100)
        self.spin_quality_percent.setValue(_DEFAULT_QUALITY_PCT)
        self.spin_quality_percent.setSuffix(' %')
        self.spin_quality_percent.setFixedWidth(80)
        q3.addWidget(self.combo_quality_preset, 1)
        q3.addWidget(self.spin_quality_percent)
        lay.addLayout(q3)

        # Row 4 - horizontal slider, kept in sync with the spin box.
        self.slider_quality_percent = QSlider(Qt.Horizontal)
        self.slider_quality_percent.setRange(1, 100)
        self.slider_quality_percent.setValue(_DEFAULT_QUALITY_PCT)
        lay.addWidget(self.slider_quality_percent)

        return card

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self.fmt_combo.currentIndexChanged.connect(self._refresh_interlocks)
        self.fmt_combo.currentIndexChanged.connect(self.options_changed.emit)

        self.radio_quality_size.toggled.connect(self._refresh_interlocks)
        self.radio_quality_percent.toggled.connect(self._refresh_interlocks)
        self.radio_quality_size.toggled.connect(self.options_changed.emit)
        self.radio_quality_percent.toggled.connect(self.options_changed.emit)

        self.spin_limit_mb.valueChanged.connect(self.options_changed.emit)

        # Preset combo pushes its value into both the spin and slider.
        self.combo_quality_preset.currentIndexChanged.connect(
            self._on_quality_preset_changed)

        # Spin <-> slider: two-way sync with the "only if different"
        # guard from preset_export_demo to avoid signal loops.
        self.spin_quality_percent.valueChanged.connect(self._on_spin_percent_changed)
        self.slider_quality_percent.valueChanged.connect(self._on_slider_percent_changed)

    def _refresh_interlocks(self) -> None:
        fmt = self.fmt_combo.currentData() or ''
        tiff = fmt in (FileFormat.TIFF_8BIT.value, FileFormat.TIFF_16BIT.value)
        # TIFF is effectively lossless - grey out every Quality control.
        for w in (self.radio_quality_size, self.radio_quality_percent):
            w.setEnabled(not tiff)
        if tiff:
            for w in (self.spin_limit_mb, self.combo_quality_preset,
                      self.spin_quality_percent, self.slider_quality_percent):
                w.setEnabled(False)
            return
        is_size = self.radio_quality_size.isChecked()
        self.spin_limit_mb.setEnabled(is_size)
        self.combo_quality_preset.setEnabled(not is_size)
        self.spin_quality_percent.setEnabled(not is_size)
        self.slider_quality_percent.setEnabled(not is_size)

    # ------------------------------------------------------------------
    # Slot helpers (percent sync)
    # ------------------------------------------------------------------

    def _on_quality_preset_changed(self) -> None:
        v = self.combo_quality_preset.currentData()
        if v is None:
            return
        v = int(v)
        self.spin_quality_percent.setValue(v)
        self.slider_quality_percent.setValue(v)

    def _on_spin_percent_changed(self, v: int) -> None:
        if self.slider_quality_percent.value() != v:
            self.slider_quality_percent.setValue(v)
        self.options_changed.emit()

    def _on_slider_percent_changed(self, v: int) -> None:
        if self.spin_quality_percent.value() != v:
            self.spin_quality_percent.setValue(v)
        # spin.setValue above will emit options_changed through
        # _on_spin_percent_changed; only re-emit if the spin was
        # already at the same value (slider jog without spin change).
        else:
            self.options_changed.emit()

    # ------------------------------------------------------------------
    # Public API - UI <-> dict
    # ------------------------------------------------------------------

    def to_options(self) -> dict:
        """Build an ``ExportOptions`` dict from the current UI state.

        Always emits ``file_format`` plus the active quality knob; other
        ``ExportOptions`` fields (scale, DPI, sharpen, naming, ...) are
        intentionally *not* touched so the host keeps the active
        preset's values for them.
        """
        opts = ExportOptions()
        fmt = self.fmt_combo.currentData()
        if fmt:
            opts.file_format(fmt)

        fmt_value = fmt or ''
        tiff = fmt_value in (FileFormat.TIFF_8BIT.value, FileFormat.TIFF_16BIT.value)
        if not tiff:
            if self.radio_quality_size.isChecked():
                mb = float(self.spin_limit_mb.value())
                if mb > 0:
                    opts.limit_size(mb)
            else:
                pct = int(self.spin_quality_percent.value())
                if pct > 0:
                    opts.quality(pct)

        return opts.build()

    def load_options(self, d: dict | None) -> None:
        """Re-populate from a persisted options dict. Missing keys fall
        back to the widget defaults (JPG, Percent 80%)."""
        d = dict(d or {})
        blocker = self.blockSignals(True)
        try:
            self._load_options_no_signals(d)
        finally:
            self.blockSignals(blocker)
        self._refresh_interlocks()
        self.options_changed.emit()

    def _load_options_no_signals(self, d: dict) -> None:
        # Format - first item (JPG) is the implicit default.
        fmt = d.get(ExportOptions.KEY_FILE_FORMAT)
        matched = False
        if fmt is not None:
            for i in range(self.fmt_combo.count()):
                if self.fmt_combo.itemData(i) == fmt:
                    self.fmt_combo.setCurrentIndex(i)
                    matched = True
                    break
        if not matched:
            self.fmt_combo.setCurrentIndex(0)

        # Quality - pick the radio that matches the stored type (or the
        # inferred type if only a value was persisted).
        qt = d.get(ExportOptions.KEY_QUALITY_TYPE)
        if qt == QualityType.SIZE.value or ExportOptions.KEY_LIMIT_SIZE in d:
            self.radio_quality_size.setChecked(True)
        else:
            self.radio_quality_percent.setChecked(True)

        mb = d.get(ExportOptions.KEY_LIMIT_SIZE)
        if isinstance(mb, (int, float)) and mb > 0:
            self.spin_limit_mb.setValue(int(mb))
        pct = d.get(ExportOptions.KEY_QUALITY)
        if isinstance(pct, (int, float)) and pct > 0:
            v = max(1, min(100, int(pct)))
            self.spin_quality_percent.setValue(v)
            self.slider_quality_percent.setValue(v)

    # ------------------------------------------------------------------
    # Summary helper - compact string for list / table cells.
    # ------------------------------------------------------------------

    @staticmethod
    def summary(opts: dict | None) -> str:
        if not opts:
            return 'default'
        parts: list[str] = []
        fmt = opts.get(ExportOptions.KEY_FILE_FORMAT)
        if fmt:
            parts.append({
                FileFormat.JPEG.value: 'JPG',
                FileFormat.PNG.value: 'PNG',
                FileFormat.TIFF_8BIT.value: 'TIFF8',
                FileFormat.TIFF_16BIT.value: 'TIFF16',
                FileFormat.ORIGINAL.value: 'ORIG',
            }.get(fmt, str(fmt).upper()))
        q = opts.get(ExportOptions.KEY_QUALITY)
        if q:
            parts.append(f'q{q}')
        ls = opts.get(ExportOptions.KEY_LIMIT_SIZE)
        if ls:
            parts.append(f'≤{int(ls)}MB')
        st = opts.get(ExportOptions.KEY_SCALE_TYPE)
        if st == ScaleType.LONG_EDGE.value:
            le = opts.get(ExportOptions.KEY_SCALE_LONG_EDGE)
            if le:
                parts.append(f'long={le}px')
        return ' '.join(parts) if parts else 'default'
