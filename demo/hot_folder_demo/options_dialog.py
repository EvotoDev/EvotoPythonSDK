"""Per-row ExportOptions editor.

Thin wrapper around :class:`demo.shared.ExportOptionsPanel` - the
shared Format + Quality card from ``preset_export_demo``. Every other
``ExportOptions`` knob (scale / DPI / sharpen / naming / ...) stays on
the active preset suit: the host applies its own fallbacks for keys
the dict does not carry, so per-lane dicts stay tiny and easy to
reason about.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QVBoxLayout,
)

from demo.shared import ExportOptionsPanel, apply_theme


class OptionsDialog(QDialog):
    """Edit a mapping row's ``ExportOptions`` dict.

    Run the dialog modally, then read :meth:`result_options` - returns
    the new dict on OK, or the unchanged original on Cancel.
    """

    def __init__(self, options: dict | None = None, parent=None):
        super().__init__(parent)
        self._initial = dict(options or {})
        self._result: dict = dict(self._initial)

        self.setWindowTitle('Export Options')
        self.setModal(True)
        self.resize(420, 320)

        self._build_ui()
        self.panel.load_options(self._initial)
        apply_theme(self)

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        hint = QLabel(
            'Pick the output format and quality for this lane. '
            'Everything else (scale, naming, sharpen, ...) follows '
            'the selected preset suit.')
        hint.setWordWrap(True)
        hint.setProperty('ev_role', 'section-caption')
        root.addWidget(hint)

        self.panel = ExportOptionsPanel()
        root.addWidget(self.panel)
        root.addStretch(1)

        self.btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        self.btns.accepted.connect(self._on_accept)
        self.btns.rejected.connect(self.reject)
        self.btns.button(QDialogButtonBox.Ok).setProperty('ev_role', 'primary')
        root.addWidget(self.btns)

    # ------------------------------------------------------------------

    def _on_accept(self) -> None:
        self._result = self.panel.to_options()
        self.accept()

    def result_options(self) -> dict:
        return self._result

    @staticmethod
    def summary(opts: dict | None) -> str:
        """Short human-readable string for the table's Options column."""
        return ExportOptionsPanel.summary(opts)
