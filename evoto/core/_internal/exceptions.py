"""Internal SDK exceptions."""

from dataclasses import dataclass


@dataclass
class ReplyStatus:
    """
    Callback status (similar to the host-side auto-reply status struct).

    Passed to async callbacks with timing and outcome metadata.

    Attributes:
        request_id: Unique request id.
        send_timestamp: Wall time when the request was sent (seconds).
        recv_timestamp: Wall time when the response arrived (seconds).
        elapsed_ms: Round-trip latency in milliseconds.
        is_timeout: True if the call ended due to timeout.
        is_success: True if the call succeeded.
        error_code: Present when is_success is False.
        error_message: Present when is_success is False.
    """
    request_id: str
    send_timestamp: float
    recv_timestamp: float = 0.0
    elapsed_ms: float = 0.0
    is_timeout: bool = False
    is_success: bool = True
    error_code: int = 0
    error_message: str = ""

    def __post_init__(self):
        """Compute elapsed_ms when recv is set."""
        if self.recv_timestamp > 0 and self.elapsed_ms == 0:
            self.elapsed_ms = (self.recv_timestamp - self.send_timestamp) * 1000


class PluginError(Exception):
    """Base plugin error."""
    pass


class SocketConnectionError(PluginError):
    """
    Socket / connection failure.

    Note: not named ConnectionError to avoid shadowing the builtin.
    """
    pass


class ApiError(PluginError):
    """Host API error response."""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class TaskError(PluginError):
    """Task execution error."""
    pass


class TaskNotFoundError(PluginError):
    """Requested task is not registered in the plugin's TaskRegistry.

    Mapped to ``ApiErrorCode.NOT_FOUND (404)`` when reported to the host.
    """
    def __init__(self, task_name: str):
        self.task_name = task_name
        super().__init__(f"Task not found: {task_name}")


class RequestTimeoutError(PluginError):
    """
    Request timed out.

    Note: not named TimeoutError to avoid shadowing the builtin.
    """
    pass


class IncompatibleVersionError(PluginError):
    """
    Version mismatch between SDK and host (or plugin constraints).
    """
    pass
