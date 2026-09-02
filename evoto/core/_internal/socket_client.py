"""Stream-oriented IPC client with PacketCodec v2 framing.

Talks to the host's local socket. The host transport is
platform-split:

- **POSIX** - Unix Domain Socket (``$TMPDIR/<name>``), spoken over
  :mod:`socket` ``AF_UNIX``.
- **Windows** - Named pipe (``\\\\.\\pipe\\<name>``), spoken over
  :mod:`ctypes` via :class:`WinPipeClient`.

This module picks the right transport at ``connect`` time based on
``sys.platform`` and the shape of ``socket_path``, then drives both
with the same packet-framed send/receive loop so the upper layers do
not care which one is in use.
"""

import socket
import sys
import threading
import json
import logging
import time
from typing import Any, Callable

from .exceptions import SocketConnectionError
from .packet_codec import PacketCodec
from ..ipc_constants import is_windows_pipe_path

logger = logging.getLogger(__name__)

# Internal dict key where binary attachment is surfaced after decode
BINARY_DATA_KEY = "__evoto_binary_data__"

_IS_WINDOWS = sys.platform == "win32"


def _create_transport(socket_path: str, timeout: float):
    """Build the right transport for ``socket_path``.

    Returns an object exposing ``sendall(bytes)``, ``recv(int) -> bytes``
    and ``close()``. On POSIX that is a plain :class:`socket.socket`;
    on Windows it is :class:`WinPipeClient`.

    Guarantees the underlying handle is released if the initial connect
    fails, so a tight retry loop cannot accumulate dangling fds / pipe
    handles between attempts.
    """
    want_pipe = _IS_WINDOWS or is_windows_pipe_path(socket_path)
    if want_pipe:
        # Imported lazily: the module uses :mod:`ctypes.wintypes` and
        # would fail to import on non-Windows in some stripped envs.
        from .win_pipe import WinPipeClient

        pipe = WinPipeClient()
        try:
            pipe.connect(socket_path, timeout=timeout)
        except BaseException:
            pipe.close()
            raise
        return pipe

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(socket_path)
    except BaseException:
        sock.close()
        raise
    return sock


class SocketClient:
    """Local-socket client (UDS on POSIX, named pipe on Windows)."""

    def __init__(self):
        """Init transport / receiver thread state."""
        # ``_socket`` is named for historical reasons; it holds either
        # a real :class:`socket.socket` (POSIX) or a
        # :class:`WinPipeClient` (Windows). Both expose
        # ``sendall`` / ``recv`` / ``close``.
        self._socket: Any = None
        self._connected: bool = False
        self._receiver_thread: threading.Thread | None = None
        self._message_callback: Callable[[dict[str, Any]], None] | None = None
        self._disconnect_callback: Callable[[], None] | None = None
        self._running = False
        # ``_state_lock`` protects the small, fast state-flag +
        # transport-handle swap operations (connect / disconnect /
        # is_connected / receiver snapshot). It is NEVER held across
        # blocking I/O so short control-plane calls cannot stall behind
        # a slow ``sendall`` on a backpressured pipe.
        self._state_lock = threading.Lock()
        # ``_send_lock`` serialises concurrent producers so their framed
        # packets do not interleave on the wire; it is held across
        # ``sendall`` but not across any state mutation.
        self._send_lock = threading.Lock()
        # Back-compat alias: some older callers / tests may still reach
        # for ``_lock``. Point it at the state lock, which preserves the
        # historical "fast" semantics.
        self._lock = self._state_lock

    def connect(self, socket_path: str, timeout: float = 5.0) -> None:
        """
        Connect to host local socket / named pipe.

        Args:
            socket_path: UDS filesystem path (POSIX) or named-pipe
                address (Windows, e.g. ``\\\\.\\pipe\\pro_evoto_plugin_host``).
            timeout: retry window in seconds
        """
        start_time = time.time()
        last_error: Exception | None = None

        while time.time() - start_time < timeout:
            try:
                transport = _create_transport(
                    socket_path,
                    timeout=max(0.1, timeout - (time.time() - start_time)),
                )
                with self._state_lock:
                    self._socket = transport
                    self._connected = True
                    self._running = True
                logger.info(f"Connected to socket: {socket_path}")
                return
            except SocketConnectionError:
                # WinPipeClient already exhausted its own retry budget.
                # Surface immediately; retrying here would double-wait.
                raise
            except Exception as e:
                last_error = e
                time.sleep(0.5)

        raise SocketConnectionError(f"Failed to connect to {socket_path}: {last_error}")

    def disconnect(self) -> None:
        """Close transport and notify optional disconnect callback."""
        with self._state_lock:
            was_connected = self._connected
            self._running = False
            transport = self._socket
            self._socket = None
            self._connected = False

        if transport is not None:
            try:
                transport.close()
            except Exception:
                pass

        if was_connected:
            logger.info("Disconnected from socket")
            if self._disconnect_callback:
                try:
                    self._disconnect_callback()
                except Exception as e:
                    logger.error(f"Error in disconnect callback: {e}")

    def set_disconnect_callback(self, callback: Callable[[], None]) -> None:
        """Called from receiver thread when connection ends."""
        self._disconnect_callback = callback

    def send_message(self, message: dict[str, Any], binary_data: bytes = None) -> None:
        """
        Send one JSON message with optional binary tail.

        Locking is split so a slow / backpressured ``sendall`` cannot
        freeze the state lock that :meth:`is_connected`,
        :meth:`disconnect`, and the receiver loop all hit on their
        fast paths:

        - ``_state_lock`` is taken briefly to snapshot the live transport
          under the "still connected" invariant, then released.
        - ``_send_lock`` is held across the blocking ``sendall`` to
          guarantee framed packets from concurrent producers do not
          interleave on the wire.

        On failure we surface the original Win32 / OS error message
        (``[WinError 109] The pipe has been ended.`` &c.) instead of
        swallowing it into a bare ``"Send failed"`` - debuggability on
        Windows depends on this.

        Args:
            message: dict serialized to JSON
            binary_data: optional attachment (pixels, files, ...)
        """
        json_data = json.dumps(message).encode('utf-8')
        packet = PacketCodec.encode(json_data, binary_data or b'')

        with self._state_lock:
            if not self._connected or not self._socket:
                raise SocketConnectionError("Not connected")
            transport = self._socket

        send_error: BaseException | None = None
        with self._send_lock:
            # Re-check state under the send lock: a concurrent
            # ``disconnect`` may have raced us between the snapshot
            # above and grabbing the send lock.
            with self._state_lock:
                if not self._connected or self._socket is not transport:
                    raise SocketConnectionError("Not connected")
            try:
                transport.sendall(packet)
                return
            except Exception as e:
                send_error = e

        # sendall raised - tear the channel down and surface the root
        # cause so callers can log / retry intelligently.
        self.disconnect()
        raise SocketConnectionError(f"Send failed: {send_error}") from send_error

    def start_receiver(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """
        Spawn background reader thread.

        Args:
            callback: invoked per decoded message
        """
        self._message_callback = callback
        self._receiver_thread = threading.Thread(target=self._receiver_loop, daemon=True)
        self._receiver_thread.start()

    def _receiver_loop(self) -> None:
        """Receive loop using PacketCodec v2 and a bytearray buffer."""
        buffer = bytearray()
        while True:
            with self._state_lock:
                if not self._running or not self._socket:
                    break
                transport = self._socket

            try:
                chunk = transport.recv(65536)
                if not chunk:
                    logger.info("Socket connection closed by remote")
                    break

                buffer.extend(chunk)
                packets, buffer = PacketCodec.decode(buffer)

                for json_data, binary_data in packets:
                    try:
                        message = json.loads(json_data.decode('utf-8'))
                        if binary_data:
                            message[BINARY_DATA_KEY] = binary_data
                        if self._message_callback:
                            try:
                                self._message_callback(message)
                            except Exception as e:
                                logger.error(f"Error in message callback: {e}")
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON received: {json_data[:200]}")

            except Exception as e:
                with self._state_lock:
                    still_running = self._running
                if still_running:
                    logger.error(f"Socket receive error: {e}")
                break

        self.disconnect()

    @property
    def is_connected(self) -> bool:
        with self._state_lock:
            return self._connected
