"""Spawn and supervise a local Evoto host process for the demo.

The hot-folder demo can optionally launch Evoto for users who want a
one-step local workflow. On macOS, selecting an ``.app`` bundle is
supported; the launcher resolves it to the executable inside the bundle.

The launcher only tracks processes it starts itself. If Evoto was
started outside the demo, ``stop()`` does not affect that process.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal


# Windows process-creation flags used to keep the demo launcher quiet.
_CREATE_NO_WINDOW = 0x08000000
_DETACHED_PROCESS = 0x00000008


def resolve_binary(path: str) -> str:
    """Return the executable path to feed to :class:`subprocess.Popen`.

    * On macOS, accept either the ``.app`` bundle root or the Mach-O
      binary itself. When given a bundle we look up
      ``Contents/MacOS/<bundle stem>``, falling back to the first
      executable file under ``Contents/MacOS`` - this covers both the
      canonical layout and the dev build whose binary name may not
      match the bundle folder.
    * On other platforms the input is returned unchanged.
    """
    if not path:
        return ''
    p = Path(path)
    if sys.platform == 'darwin' and p.suffix == '.app' and p.is_dir():
        macos_dir = p / 'Contents' / 'MacOS'
        if macos_dir.is_dir():
            preferred = macos_dir / p.stem
            if preferred.exists():
                return str(preferred)
            for child in sorted(macos_dir.iterdir()):
                if child.is_file() and os.access(child, os.X_OK):
                    return str(child)
    return str(p)


class EvotoLauncher(QObject):
    """Spawn and monitor an Evoto child process.

    Signals:
        log(str):   human-readable status updates.
        launched(int): emitted with the pid right after a successful spawn.
        exited(int):   emitted with the exit code when the child dies.
    """

    log = Signal(str)
    launched = Signal(int)
    exited = Signal(int)

    # Poll the child every 500 ms so ``exited`` fires within half a
    # second of the host crashing or being quit by the user.
    _POLL_INTERVAL_MS = 500

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc: Optional[subprocess.Popen] = None
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(self._POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._poll)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_running(self) -> bool:
        """Is *our* child process still alive?

        This only reports on processes started through :meth:`start`; a
        separately launched Evoto doesn't show up here.
        """
        return self._proc is not None and self._proc.poll() is None

    def start(self, path: str) -> tuple[bool, str]:
        """Launch Evoto silently. Returns ``(ok, error_message)``.

        Calling this while a child is already running is a no-op and
        returns ``(True, "")`` - the caller can simply flip the
        auto-connect loop on without worrying about duplicate children.
        """
        if self.is_running():
            return True, ''
        if not path:
            return False, 'Evoto executable path is empty.'

        binary = resolve_binary(path)
        if not os.path.exists(binary):
            return False, f'Evoto binary not found: {binary}'
        if sys.platform != 'win32' and not os.access(binary, os.X_OK):
            return False, f'Evoto binary is not executable: {binary}'

        cmd = [binary, '-silent']
        kwargs: dict = dict(
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if sys.platform == 'win32':
            kwargs['creationflags'] = _CREATE_NO_WINDOW | _DETACHED_PROCESS
        else:
            # Detach from our controlling terminal so Ctrl+C on the demo
            # doesn't also kill Evoto.
            kwargs['start_new_session'] = True

        try:
            self._proc = subprocess.Popen(cmd, **kwargs)
        except OSError as exc:
            return False, f'Failed to launch {binary}: {exc}'

        pid = self._proc.pid
        self.log.emit(f'Launched Evoto (pid={pid}) - {binary} -silent')
        self.launched.emit(pid)
        self._poll_timer.start()
        return True, ''

    def stop(self, timeout_s: float = 5.0) -> None:
        """Terminate the child process, SIGKILL as last resort."""
        if not self.is_running():
            return
        assert self._proc is not None
        pid = self._proc.pid
        try:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=timeout_s)
                self.log.emit(f'Stopped Evoto (pid={pid})')
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self.log.emit(f'Killed Evoto (pid={pid}) after timeout')
        except OSError as exc:
            self.log.emit(f'Stop Evoto failed (pid={pid}): {exc}')

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _poll(self) -> None:
        """Watch for the child dying so the UI can mirror the state."""
        if self._proc is None:
            self._poll_timer.stop()
            return
        rc = self._proc.poll()
        if rc is None:
            return
        self._poll_timer.stop()
        self.log.emit(f'Evoto child exited (rc={rc})')
        # Clear the handle *before* emitting so slots observing the
        # signal see ``is_running() == False``.
        self._proc = None
        self.exited.emit(rc)
