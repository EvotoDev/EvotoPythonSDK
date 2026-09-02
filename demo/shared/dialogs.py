"""Dark-theme-aware dialog helpers shared across demos.

Qt's ``QMessageBox.question/information/...`` class methods force a
center-aligned label, a fixed icon pixmap, and a platform-native button
layout - none of which match the plugin's visual language. Rather than
fight the stylesheet against ``QMessageBox`` internals, we build a small
frameless :class:`QDialog` with a fully custom layout::

    ┌──────────────────────────────────────┐
    │ Heading (the question / message)   ×  │   <- ``text`` arg
    ├──────────────────────────────────────┤   <- only if informative
    │ Optional body paragraph (details)     │   <- ``informative`` arg
    │                                       │
    │                      [No] [Yes]       │
    └──────────────────────────────────────┘

Semantic note: the ``title`` argument is used only as the OS window
title (screen-reader / task-switcher context). Inside the card the loud
heading is the ``text`` argument - i.e. the actual question or message.
Extra details go into ``informative``. That way a call like
``themed_confirm(self, 'Quit Host', 'Shut the Evoto host down now?')``
renders the question as the heading instead of the noise-word
"Quit Host".

All caller-facing helpers (:func:`themed_confirm`, :func:`themed_message`)
keep the same signature as before - swapping the implementation is
transparent to existing call sites.
"""

from __future__ import annotations

from .theme import apply_theme


# Dialog-scoped QSS layered on top of the shared ``DARK_QSS``. We rely
# on ``ev_role`` / ``#objectName`` selectors so the rules only hit the
# dialog internals and never leak into the rest of the demo UI.
_DIALOG_QSS = """
#evDialogCard {
    background: #1c1d1f;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
}
QLabel[ev_role="dialog-title"] {
    font-size: 15px; font-weight: 700;
    color: rgba(243, 240, 232, 0.95);
    padding: 0;
}
QLabel[ev_role="dialog-body"] {
    font-size: 13px;
    color: rgba(243, 240, 232, 0.80);
    padding: 0;
}
#evDialogSeparator {
    background: rgba(255, 255, 255, 0.08);
}
#evDialogClose {
    font-size: 26px; font-weight: 300;
    color: rgba(243, 240, 232, 0.68);
    background: transparent; border: none;
    border-radius: 16px; padding: 0;
}
#evDialogClose:hover {
    background: rgba(255, 255, 255, 0.08);
    color: rgba(243, 240, 232, 0.95);
}
QPushButton[ev_role="dialog-primary"],
QPushButton[ev_role="dialog-danger"],
QPushButton[ev_role="dialog-ghost"] {
    min-width: 80px; min-height: 32px;
    padding: 0 20px; border-radius: 16px;
    font-size: 13px; font-weight: 700;
}
QPushButton[ev_role="dialog-primary"] {
    background: #f0c548; color: #231a00;
    border: 1px solid rgba(240, 197, 72, 0.45);
}
QPushButton[ev_role="dialog-primary"]:hover { background: #f4cd62; }
QPushButton[ev_role="dialog-danger"] {
    background: #e5484d; color: #ffffff;
    border: 1px solid rgba(229, 72, 77, 0.45);
}
QPushButton[ev_role="dialog-danger"]:hover { background: #ee5a5e; }
QPushButton[ev_role="dialog-ghost"] {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.06);
    color: rgba(243, 240, 232, 0.85);
}
QPushButton[ev_role="dialog-ghost"]:hover {
    background: rgba(255, 255, 255, 0.12);
}
"""


def _build_dialog(parent, heading: str, window_title: str):
    """Construct an empty themed dialog.

    Returns ``(dlg, body_layout, btn_row, separator)`` - callers append
    any *additional* details via ``body_layout`` (shown below the
    separator) and action buttons via ``btn_row``. If no extra body is
    added, the caller hides ``separator`` so the card stays tight.

    Args:
        parent: Owning widget.
        heading: Loud top-of-card line - the question or the message.
        window_title: OS-level title (invisible in our frameless card
            but surfaced to screen readers / task switchers).
    """
    # Lazy Qt import so non-GUI consumers of ``demo.shared`` (e.g.
    # unit tests, CLI tools) don't pay the import cost.
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QDialog, QFrame, QHBoxLayout, QLabel, QPushButton,
        QVBoxLayout, QWidget,
    )

    dlg = QDialog(parent)
    dlg.setModal(True)
    dlg.setWindowTitle(window_title)
    # Frameless + translucent so the rounded ``#evDialogCard`` below
    # can draw its own corners. ``Qt.Dialog`` keeps modal semantics.
    dlg.setWindowFlags(
        Qt.Dialog | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint,
    )
    dlg.setAttribute(Qt.WA_TranslucentBackground)
    dlg.setMinimumWidth(440)

    outer = QVBoxLayout(dlg)
    outer.setContentsMargins(0, 0, 0, 0)

    card = QFrame(dlg)
    card.setObjectName('evDialogCard')
    outer.addWidget(card)

    root = QVBoxLayout(card)
    root.setContentsMargins(24, 20, 24, 20)
    root.setSpacing(12)

    # ---- heading row --------------------------------------------
    head_row = QHBoxLayout()
    head_row.setSpacing(8)
    head_lbl = QLabel(heading, card)
    head_lbl.setProperty('ev_role', 'dialog-title')
    head_lbl.setWordWrap(True)
    head_row.addWidget(head_lbl, 1)

    close_btn = QPushButton('\u00D7', card)  # multiplication sign
    close_btn.setObjectName('evDialogClose')
    close_btn.setFlat(True)
    close_btn.setFixedSize(32, 32)
    close_btn.setCursor(Qt.PointingHandCursor)
    close_btn.clicked.connect(dlg.reject)
    head_row.addWidget(close_btn, 0, Qt.AlignTop)
    root.addLayout(head_row)

    # ---- separator (caller hides if no body is added) -----------
    separator = QWidget(card)
    separator.setObjectName('evDialogSeparator')
    separator.setFixedHeight(1)
    root.addWidget(separator)

    # ---- body placeholder ---------------------------------------
    body_layout = QVBoxLayout()
    body_layout.setContentsMargins(0, 4, 0, 0)
    body_layout.setSpacing(4)
    root.addLayout(body_layout)
    root.addStretch(1)

    # ---- button row ---------------------------------------------
    btn_row = QHBoxLayout()
    btn_row.setContentsMargins(0, 4, 0, 0)
    btn_row.setSpacing(10)
    btn_row.addStretch(1)
    root.addLayout(btn_row)

    apply_theme(dlg)
    dlg.setStyleSheet(dlg.styleSheet() + _DIALOG_QSS)

    return dlg, body_layout, btn_row, separator


def _add_body(body_layout, text: str, role: str) -> None:
    """Append a left-aligned body label to ``body_layout``."""
    from PySide6.QtWidgets import QLabel

    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setProperty('ev_role', role)
    body_layout.addWidget(lbl)


def _add_button(btn_row, text: str, role: str, *, default: bool):
    """Append an action button to ``btn_row`` and return it."""
    from PySide6.QtWidgets import QPushButton

    btn = QPushButton(text)
    btn.setProperty('ev_role', role)
    btn.setDefault(default)
    btn.setAutoDefault(default)
    return btn


def _bring_to_front(dlg) -> None:
    """Force the dialog to the foreground and grab activation.

    A borderless (``FramelessWindowHint``) + translucent window on macOS
    does not reliably become the key window on its own - especially when
    it pops after a long-running background call, by which point the app
    may have lost foreground focus. Without key-window status the dialog
    cannot receive mouse clicks, so a blocking ``exec()`` would trap the
    main thread forever. Raising + activating (now and once more after
    the event loop settles) lets it take input as expected.
    """
    from PySide6.QtCore import QTimer

    def _activate() -> None:
        dlg.raise_()
        dlg.activateWindow()

    _activate()
    QTimer.singleShot(0, _activate)


def themed_confirm(
    parent,
    title: str,
    text: str,
    informative: str = '',
    *,
    yes_text: str = 'Yes',
    no_text: str = 'No',
    default_yes: bool = False,
    danger: bool = False,
) -> bool:
    """Dark-theme confirmation dialog with a primary-yellow Yes button.

    Drop-in replacement for ``QMessageBox.question(...)``.

    Args:
        parent: Owning widget - usually ``self`` from a QWidget subclass.
        title: OS window title (invisible in the frameless card but
            surfaced to screen readers / task switchers). Not rendered
            inside the card.
        text: Loud heading at the top of the card - typically the
            actual question ("Delete the Project?").
        informative: Optional body paragraph shown below a separator.
        yes_text / no_text: Button labels.
        default_yes: Which button the Enter key activates. Defaults to
            ``False`` so Enter never triggers a destructive action by
            accident - opt in with ``default_yes=True`` for benign
            confirmations.
        danger: When ``True`` the accept button renders in the
            destructive-red palette instead of the primary-yellow one.
            Use for confirmations that lead to data loss (delete,
            remove, wipe, ...). Callers should usually also set
            ``yes_text='Delete'`` (or similar action verb) so the
            button label, colour, and semantics all align.

    Returns:
        ``True`` when the user clicked Yes, ``False`` for No / Esc /
        window close.
    """
    dlg, body_layout, btn_row, separator = _build_dialog(
        parent, heading=text, window_title=title)
    if informative:
        _add_body(body_layout, informative, 'dialog-body')
    else:
        # No body paragraph -> hide the separator so the card stays
        # tight (heading + buttons, no dangling rule).
        separator.hide()

    yes_role = 'dialog-danger' if danger else 'dialog-primary'
    no_btn = _add_button(btn_row, no_text, 'dialog-ghost',
                         default=not default_yes)
    yes_btn = _add_button(btn_row, yes_text, yes_role,
                          default=default_yes)
    no_btn.clicked.connect(dlg.reject)
    yes_btn.clicked.connect(dlg.accept)
    btn_row.addWidget(no_btn)
    btn_row.addWidget(yes_btn)

    _bring_to_front(dlg)
    # ``exec()`` returns ``QDialog.Accepted`` (1) / ``Rejected`` (0);
    # reject covers No, Esc, and the × button.
    return bool(dlg.exec())


def themed_message(
    parent,
    title: str,
    text: str,
    informative: str = '',
    *,
    ok_text: str = 'OK',
) -> None:
    """Dark-theme single-button dialog for info / warning / error notices.

    Drop-in replacement for ``QMessageBox.information(...)`` /
    ``QMessageBox.warning(...)`` / ``QMessageBox.critical(...)``. The
    severity those three convey via coloured pixmaps is already carried
    by the dialog ``title`` (e.g. ``"Import Failed"``), so we drop the
    stock icons - they render as muddy near-black sprites on our dark
    background - and render plain text with a single primary-yellow
    OK button.

    Args:
        parent: Owning widget - usually ``self`` from a QWidget subclass.
        title: OS window title (accessibility only; not rendered in the
            card). Use an action-led phrase (e.g. ``"Import Failed"``).
        text: Loud heading - the actual message to surface. Callers
            should keep it short; push long details (stack traces,
            multi-sentence explanations) into ``informative``.
        informative: Optional body paragraph shown below a separator.
        ok_text: Label on the dismiss button.
    """
    dlg, body_layout, btn_row, separator = _build_dialog(
        parent, heading=text, window_title=title)
    if informative:
        _add_body(body_layout, informative, 'dialog-body')
    else:
        separator.hide()

    ok_btn = _add_button(btn_row, ok_text, 'dialog-primary', default=True)
    ok_btn.clicked.connect(dlg.accept)
    btn_row.addWidget(ok_btn)

    _bring_to_front(dlg)
    dlg.exec()


def themed_notify(
    parent,
    title: str,
    text: str,
    informative: str = '',
    *,
    ok_text: str = 'OK',
):
    """Non-blocking dark-theme notice for async failures / timeouts.

    Unlike :func:`themed_message` this does **not** run a nested modal
    event loop (``exec()``). It shows a non-modal dialog and returns
    immediately, so the caller's slot finishes and the main event loop
    keeps running.

    This matters for notices raised from background work (e.g. a request
    that timed out after ~30s): a borderless + translucent *modal* dialog
    can fail to become the key window on macOS when the app is no longer
    in the foreground, leaving ``exec()`` trapping the main thread with
    an unclickable popup - i.e. the whole app appears frozen and needs a
    force quit. A non-modal dialog can never trap the loop, so the app
    always stays responsive.

    Args:
        parent: Owning widget - keeps the dialog alive (parent ownership)
            so the non-modal window is not garbage-collected immediately.
        title: OS window title (accessibility only).
        text: Loud heading - the message to surface.
        informative: Optional body paragraph shown below a separator.
        ok_text: Label on the dismiss button.

    Returns:
        The created :class:`QDialog` (already shown).
    """
    from PySide6.QtCore import Qt

    dlg, body_layout, btn_row, separator = _build_dialog(
        parent, heading=text, window_title=title)
    if informative:
        _add_body(body_layout, informative, 'dialog-body')
    else:
        separator.hide()

    ok_btn = _add_button(btn_row, ok_text, 'dialog-primary', default=True)
    ok_btn.clicked.connect(dlg.close)
    btn_row.addWidget(ok_btn)

    dlg.setModal(False)
    # Delete on close so stacked notices don't accumulate; parent
    # ownership keeps it alive until the user dismisses it.
    dlg.setAttribute(Qt.WA_DeleteOnClose)
    dlg.show()
    _bring_to_front(dlg)
    return dlg
