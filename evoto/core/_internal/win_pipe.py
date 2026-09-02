"""Win32 named-pipe client with a ``socket.socket``-shaped API.

On Windows the host listens on a **named pipe**
(``\\\\.\\pipe\\<name>``), not a Unix Domain Socket. The Python
:mod:`socket` module has no way to connect to a named pipe, so this
module wraps ``kernel32`` with :mod:`ctypes` and exposes just enough
of the ``socket.socket`` surface (``sendall`` / ``recv`` / ``close``)
for :class:`evoto.core._internal.socket_client.SocketClient` to reuse
its POSIX receive loop unchanged.

Transport model - why this uses ``FILE_FLAG_OVERLAPPED``
--------------------------------------------------------
The transport is full-duplex: one background receiver thread sits in
:meth:`recv` waiting on host bytes, while a second (user / API) thread
publishes requests via :meth:`sendall`. If the pipe handle is opened
**synchronously** (no ``FILE_FLAG_OVERLAPPED``), Windows serialises
I/O on that handle inside the kernel - the second caller blocks
behind the first until the first completes. For a duplex pipe that
means the writer cannot push the first request until the reader
returns, but the reader will only return when the server replies to
that same request; the client deadlocks itself at the very first
handshake send.

Opening with ``FILE_FLAG_OVERLAPPED`` and driving each
``ReadFile`` / ``WriteFile`` with its own ``OVERLAPPED`` + event
breaks that tie: reads and writes run concurrently from the caller's
point of view while still being synchronous at the Python API level
(``recv`` / ``sendall`` block only on their own completion).

Keeps zero runtime deps - pure stdlib :mod:`ctypes`.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import time

from .exceptions import SocketConnectionError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Win32 constants & ctypes prototypes
# ---------------------------------------------------------------------------

_GENERIC_READ = 0x80000000
_GENERIC_WRITE = 0x40000000
_OPEN_EXISTING = 3
_FILE_FLAG_OVERLAPPED = 0x40000000
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

_ERROR_FILE_NOT_FOUND = 2
_ERROR_ACCESS_DENIED = 5
_ERROR_INVALID_HANDLE = 6
_ERROR_BROKEN_PIPE = 109
_ERROR_PIPE_BUSY = 231
_ERROR_PIPE_NOT_CONNECTED = 233
_ERROR_IO_PENDING = 997
_ERROR_OPERATION_ABORTED = 995

_WAIT_OBJECT_0 = 0x00000000
_WAIT_TIMEOUT = 0x00000102
_WAIT_FAILED = 0xFFFFFFFF
_INFINITE = 0xFFFFFFFF

# Hint appended to SocketConnectionError when CreateFileW returns
# ERROR_ACCESS_DENIED. Almost always a UAC / integrity-level mismatch:
# the Evoto host runs elevated (installer, administrator shell, ...) and
# the plugin runs as a standard user, or vice-versa. Windows refuses to
# open the pipe across integrity boundaries even if the DACL permits it.
_ACCESS_DENIED_HINT = (
    " - this usually means the Evoto host and the plugin are running at "
    "different integrity levels. Start both with matching UAC elevation "
    "(either both as administrator, or both as the current user)."
)

_NMPWAIT_USE_DEFAULT_WAIT = 0x00000000

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_CreateFileW = _kernel32.CreateFileW
_CreateFileW.argtypes = [
    wintypes.LPCWSTR,
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.c_void_p,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.HANDLE,
]
_CreateFileW.restype = wintypes.HANDLE

_WaitNamedPipeW = _kernel32.WaitNamedPipeW
_WaitNamedPipeW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD]
_WaitNamedPipeW.restype = wintypes.BOOL


class _OVERLAPPED(ctypes.Structure):
    """Minimal ``OVERLAPPED`` layout used by async ReadFile / WriteFile.

    We only consume ``Internal`` / ``InternalHigh`` (set by the kernel
    as status + byte count) and ``hEvent`` (we create, sign, wait, and
    close it per call). ``Offset`` / ``OffsetHigh`` are irrelevant for
    pipes but must be zero-initialised.
    """

    _fields_ = [
        ("Internal", ctypes.c_void_p),
        ("InternalHigh", ctypes.c_void_p),
        ("Offset", wintypes.DWORD),
        ("OffsetHigh", wintypes.DWORD),
        ("hEvent", wintypes.HANDLE),
    ]


_ReadFile = _kernel32.ReadFile
_ReadFile.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
    ctypes.POINTER(_OVERLAPPED),
]
_ReadFile.restype = wintypes.BOOL

_WriteFile = _kernel32.WriteFile
_WriteFile.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
    ctypes.POINTER(_OVERLAPPED),
]
_WriteFile.restype = wintypes.BOOL

_GetOverlappedResult = _kernel32.GetOverlappedResult
_GetOverlappedResult.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(_OVERLAPPED),
    ctypes.POINTER(wintypes.DWORD),
    wintypes.BOOL,
]
_GetOverlappedResult.restype = wintypes.BOOL

_CreateEventW = _kernel32.CreateEventW
_CreateEventW.argtypes = [
    ctypes.c_void_p,  # lpEventAttributes
    wintypes.BOOL,    # bManualReset
    wintypes.BOOL,    # bInitialState
    wintypes.LPCWSTR, # lpName
]
_CreateEventW.restype = wintypes.HANDLE

_WaitForSingleObject = _kernel32.WaitForSingleObject
_WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
_WaitForSingleObject.restype = wintypes.DWORD

_CloseHandle = _kernel32.CloseHandle
_CloseHandle.argtypes = [wintypes.HANDLE]
_CloseHandle.restype = wintypes.BOOL

# ``CancelIoEx`` unblocks a pending ``ReadFile`` / ``WriteFile`` on the
# receiver thread when another thread closes the transport (Vista+).
_CancelIoEx = _kernel32.CancelIoEx
_CancelIoEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(_OVERLAPPED)]
_CancelIoEx.restype = wintypes.BOOL


def _is_valid_handle(handle) -> bool:
    if handle is None:
        return False
    try:
        value = int(handle)
    except (TypeError, ValueError):
        return False
    return value != 0 and value != _INVALID_HANDLE_VALUE


class WinPipeClient:
    """Blocking client for a Windows named pipe.

    Mirrors the subset of :class:`socket.socket` that
    :class:`evoto.core._internal.socket_client.SocketClient` needs:

    - :meth:`sendall` - write all bytes or raise.
    - :meth:`recv`    - block for bytes; return ``b''`` when the pipe
      is closed / cancelled (mirrors POSIX socket ``recv`` semantics).
    - :meth:`close`   - idempotent; cancels a pending ``ReadFile`` in
      another thread so the receiver loop can exit promptly.

    The handle is opened with :data:`_FILE_FLAG_OVERLAPPED` so the
    receiver thread's :meth:`recv` and the user / API thread's
    :meth:`sendall` do NOT serialise behind each other at the kernel
    level - see the module docstring for the deadlock this avoids.
    """

    def __init__(self) -> None:
        self._handle: int | None = None
        self._path: str = ""

    # -- lifecycle ---------------------------------------------------

    def connect(self, pipe_path: str, timeout: float = 5.0) -> None:
        """Open ``pipe_path``, waiting up to ``timeout`` seconds if busy.

        Args:
            pipe_path: fully-qualified pipe name, e.g.
                ``\\\\.\\pipe\\pro_evoto_plugin_host``.
            timeout: total wall-clock budget; covers both
                "pipe not ready yet" retries and ``ERROR_PIPE_BUSY``
                ``WaitNamedPipeW`` calls.

        Raises:
            SocketConnectionError: on timeout or unrecoverable Win32 error.
        """
        deadline = time.time() + max(0.0, timeout)
        last_error = 0

        while True:
            handle = _CreateFileW(
                pipe_path,
                _GENERIC_READ | _GENERIC_WRITE,
                0,                         # no share
                None,                      # default security
                _OPEN_EXISTING,
                _FILE_FLAG_OVERLAPPED,     # required: async I/O so concurrent
                                           # read+write from different threads
                                           # do not serialise in the kernel.
                None,
            )
            if _is_valid_handle(handle):
                self._handle = int(handle)
                self._path = pipe_path
                logger.info(
                    "Connected to named pipe: %s (overlapped, handle=0x%x)",
                    pipe_path, self._handle,
                )
                return

            last_error = ctypes.get_last_error()
            remaining = deadline - time.time()

            if last_error == _ERROR_PIPE_BUSY:
                wait_ms = max(1, min(5000, int(remaining * 1000)))
                # WaitNamedPipeW returns quickly once an instance is free.
                _WaitNamedPipeW(pipe_path, wait_ms)
            elif last_error == _ERROR_FILE_NOT_FOUND:
                # Host not listening (yet). Short sleep, retry until deadline.
                if remaining <= 0:
                    break
                time.sleep(min(0.2, max(0.0, remaining)))
            else:
                # Anything else is unrecoverable (access denied, etc.).
                break

            if time.time() >= deadline:
                break

        err_text = (
            ctypes.WinError(last_error).strerror if last_error else "unknown"
        )
        hint = _ACCESS_DENIED_HINT if last_error == _ERROR_ACCESS_DENIED else ""
        raise SocketConnectionError(
            f"Failed to connect to named pipe {pipe_path}: "
            f"[WinError {last_error}] {err_text}{hint}"
        )

    def close(self) -> None:
        """Close the pipe handle, unblocking any in-flight I/O."""
        handle = self._handle
        if handle is None:
            return
        # Best-effort cancel of any pending overlapped I/O on this handle
        # (read on receiver thread, write on user thread); followed by
        # CloseHandle (idempotent). ``lpOverlapped=NULL`` cancels ALL
        # pending I/O on the handle issued by the calling process.
        try:
            _CancelIoEx(wintypes.HANDLE(handle), None)
        except OSError:
            pass
        try:
            _CloseHandle(wintypes.HANDLE(handle))
        except OSError:
            pass
        self._handle = None

    # -- I/O ---------------------------------------------------------

    def _submit_overlapped(
        self,
        op_name: str,
        op_func,
        buf_ptr: int,
        nbytes: int,
    ) -> tuple[bool, int, int]:
        """Issue one overlapped I/O call and wait for its completion.

        Returns ``(ok, transferred, last_error)`` so callers can map
        error codes to the POSIX ``recv``/``send`` semantics they want.

        On ``ERROR_IO_PENDING`` we block on the per-call event handle
        instead of the pipe handle itself, which lets the other
        direction's I/O run concurrently (see module docstring for why
        that matters).
        """
        handle = self._handle
        if handle is None:
            return (False, 0, _ERROR_INVALID_HANDLE)

        event = _CreateEventW(None, True, False, None)
        if not _is_valid_handle(event):
            err = ctypes.get_last_error()
            raise SocketConnectionError(
                f"CreateEventW failed for {op_name} on {self._path}: "
                f"[WinError {err}] {ctypes.WinError(err).strerror}"
            )

        overlapped = _OVERLAPPED()
        ctypes.memset(ctypes.byref(overlapped), 0, ctypes.sizeof(overlapped))
        overlapped.hEvent = event
        transferred = wintypes.DWORD(0)

        try:
            ok = op_func(
                wintypes.HANDLE(handle),
                ctypes.c_void_p(buf_ptr),
                nbytes,
                ctypes.byref(transferred),
                ctypes.byref(overlapped),
            )
            if not ok:
                err = ctypes.get_last_error()
                if err != _ERROR_IO_PENDING:
                    return (False, 0, err)

                # Overlapped path: kernel will signal ``event`` when the
                # operation finishes (or CancelIoEx aborts it from
                # :meth:`close`).
                wait_rc = _WaitForSingleObject(event, _INFINITE)
                if wait_rc != _WAIT_OBJECT_0:
                    wait_err = ctypes.get_last_error()
                    return (False, 0, wait_err or _ERROR_INVALID_HANDLE)

                got = _GetOverlappedResult(
                    wintypes.HANDLE(handle),
                    ctypes.byref(overlapped),
                    ctypes.byref(transferred),
                    False,
                )
                if not got:
                    return (False, transferred.value, ctypes.get_last_error())

            return (True, transferred.value, 0)
        finally:
            try:
                _CloseHandle(event)
            except OSError:
                pass

    def sendall(self, data: bytes | bytearray | memoryview) -> None:
        """Send all bytes; loop until drained or raise.

        Uses overlapped :func:`WriteFile` so a concurrent :meth:`recv`
        in another thread does not block this call at the kernel level.

        Zero-copy on the hot path:

        - ``bytes``     - pinned by CPython, passed to ``WriteFile`` via a
          ``c_char_p`` that references the object's internal buffer.
        - ``bytearray`` - exposed via ``(c_char * n).from_buffer``, which
          shares memory with the caller's buffer (no copy).
        - anything else - materialised once with ``bytes(data)``.

        We compute the base address once, then hand ``WriteFile`` an
        offset pointer per iteration, so a short write does not trigger
        a fresh slice / copy. ``pin`` is kept alive in the local frame
        for the duration of the call, preventing the underlying buffer
        from being freed out from under the kernel.

        Raises:
            SocketConnectionError: pipe is closed / other end gone.
        """
        handle = self._handle
        if handle is None:
            raise SocketConnectionError("Pipe is closed")

        if isinstance(data, (bytes, bytearray)):
            view = data
        else:
            view = bytes(data)

        size = len(view)
        if size == 0:
            return

        if isinstance(view, bytearray):
            pin = (ctypes.c_char * size).from_buffer(view)
            base_addr = ctypes.addressof(pin)
        else:
            # ``c_char_p`` keeps an internal reference to ``view`` and
            # exposes a pointer to the bytes object's stable internal
            # buffer - no copy.
            pin = ctypes.c_char_p(view)
            base_addr = ctypes.cast(pin, ctypes.c_void_p).value

        total = 0
        while total < size:
            ok, written, err = self._submit_overlapped(
                "WriteFile", _WriteFile, base_addr + total, size - total,
            )
            if not ok:
                raise SocketConnectionError(
                    f"WriteFile failed on {self._path}: "
                    f"[WinError {err}] {ctypes.WinError(err).strerror if err else 'unknown'}"
                )
            if written == 0:
                raise SocketConnectionError(
                    f"WriteFile wrote 0 bytes on {self._path}"
                )
            total += written

        # Keep ``pin`` referenced until here so the buffer backing
        # ``base_addr`` cannot be finalised mid-WriteFile on a very
        # aggressive GC build.
        del pin

    def recv(self, n: int) -> bytes:
        """Block for up to ``n`` bytes; return ``b''`` on EOF / cancel.

        Matches POSIX ``socket.recv`` semantics so
        :meth:`SocketClient._receiver_loop` can treat both transports
        identically - an empty return means "other end is gone, exit".
        """
        handle = self._handle
        if handle is None:
            return b""

        buf = (ctypes.c_ubyte * n)()
        buf_addr = ctypes.addressof(buf)

        ok, read, err = self._submit_overlapped(
            "ReadFile", _ReadFile, buf_addr, n,
        )
        if not ok:
            if err in (
                _ERROR_BROKEN_PIPE,         # host closed the pipe
                _ERROR_PIPE_NOT_CONNECTED,  # host disconnected its end
                _ERROR_OPERATION_ABORTED,   # CancelIoEx from close()
                _ERROR_INVALID_HANDLE,      # close() raced with recv
            ):
                return b""
            raise SocketConnectionError(
                f"ReadFile failed on {self._path}: "
                f"[WinError {err}] {ctypes.WinError(err).strerror if err else 'unknown'}"
            )
        if read == 0:
            return b""
        return bytes(bytearray(buf)[:read])

    @property
    def is_open(self) -> bool:
        return self._handle is not None


__all__ = ["WinPipeClient"]
