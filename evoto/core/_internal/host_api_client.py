"""Synchronous / asynchronous client for host JSON-RPC calls."""

import os
import time
import threading
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from .socket_client import SocketClient, BINARY_DATA_KEY
from .json_rpc import JsonRpc
from .exceptions import ApiError, RequestTimeoutError, ReplyStatus, TaskNotFoundError
from ..api_commands import HostCmd
from ..api_error_code import ApiErrorCode
from ..api_fields import (
    RpcField, RpcType, RpcStatus, MetaField, LogField, Field,
    EventField,
)

logger = logging.getLogger(__name__)


class PendingRequest:
    """
    In-flight request state.

    Supports blocking wait() or callback completion.
    """

    def __init__(
        self,
        request_id: str,
        callback: Callable[[Any, ReplyStatus], None] | None = None,
        timeout: float | None = None
    ):
        self.request_id = request_id
        self._event = threading.Event()
        self._result: Any = None
        self._error: Exception | None = None
        self._callback = callback
        self._timeout = timeout
        self._timeout_timer: threading.Timer | None = None
        self._send_time: float = time.time()
        self._completed: bool = False
        self._lock = threading.Lock()

    def start_timeout_timer(self) -> None:
        """Start optional timeout timer (async mode)."""
        if self._timeout and self._timeout > 0:
            self._timeout_timer = threading.Timer(
                self._timeout,
                self._on_timeout
            )
            self._timeout_timer.daemon = True
            self._timeout_timer.start()

    def cancel_timeout_timer(self) -> None:
        """Cancel timeout timer."""
        if self._timeout_timer:
            self._timeout_timer.cancel()
            self._timeout_timer = None

    def _on_timeout(self) -> None:
        """Invoked when async call times out."""
        with self._lock:
            if self._completed:
                return
        self.set_error(RequestTimeoutError(f"Request {self.request_id} timed out"), is_timeout=True)

    def wait(self, timeout: float = 30.0) -> Any:
        """Block until result or error."""
        if not self._event.wait(timeout):
            raise RequestTimeoutError(f"Request {self.request_id} timed out")
        if self._error:
            raise self._error
        return self._result

    def set_result(self, result: Any) -> None:
        """Mark success and optionally invoke callback."""
        with self._lock:
            if self._completed:
                return
            self._completed = True

        self.cancel_timeout_timer()
        self._result = result
        self._event.set()

        if self._callback:
            recv_time = time.time()
            status = ReplyStatus(
                request_id=self.request_id,
                send_timestamp=self._send_time,
                recv_timestamp=recv_time,
                elapsed_ms=(recv_time - self._send_time) * 1000,
                is_timeout=False,
                is_success=True,
                error_code=0,
                error_message=""
            )
            try:
                self._callback(result, status)
            except Exception as e:
                logger.error(f"Callback error: {e}", exc_info=True)

    def set_error(self, error: Exception, is_timeout: bool = False) -> None:
        """Mark failure and optionally invoke callback."""
        with self._lock:
            if self._completed:
                return
            self._completed = True

        self.cancel_timeout_timer()
        self._error = error
        self._event.set()

        if self._callback:
            recv_time = time.time()
            error_code = 0
            error_message = str(error)
            if isinstance(error, ApiError):
                error_code = error.code
                error_message = error.message

            status = ReplyStatus(
                request_id=self.request_id,
                send_timestamp=self._send_time,
                recv_timestamp=recv_time,
                elapsed_ms=(recv_time - self._send_time) * 1000,
                is_timeout=is_timeout,
                is_success=False,
                error_code=error_code,
                error_message=error_message
            )
            try:
                self._callback(None, status)
            except Exception as e:
                logger.error(f"Callback error: {e}", exc_info=True)

    @property
    def is_completed(self) -> bool:
        return self._completed


class HostApiClient:
    """High-level API over SocketClient."""

    #: Default pool size mirrors :class:`ThreadPoolExecutor`'s own default
    #: (``min(32, os.cpu_count() + 4)``) - enough for typical I/O fan-out
    #: without unbounded thread growth on many-core hosts.
    _DEFAULT_MAX_WORKERS = min(32, (os.cpu_count() or 1) + 4)

    def __init__(
        self,
        socket_client: SocketClient,
        auto_start_receiver: bool = True,
        max_workers: int | None = None,
    ):
        """
        Args:
            socket_client: connected transport
            auto_start_receiver: set False in unit tests
            max_workers: size of the task worker pool. Defaults to
                :attr:`_DEFAULT_MAX_WORKERS`.
        """
        self.socket_client = socket_client
        self._pending: dict[str, PendingRequest] = {}
        self._lock = threading.Lock()
        self._task_handler: Callable | None = None
        # Predicate: method name -> True means run inline on the receiver
        # thread (skip pool). Defaults to "never inline".
        self._inline_predicate: Callable[[str], bool] = lambda _m: False

        # Worker pool for host -> plugin task dispatch. Lazily created so
        # unit tests (auto_start_receiver=False + no inbound requests) do
        # not spin threads, and so reconnect cycles get a fresh pool.
        self._executor: ThreadPoolExecutor | None = None
        self._executor_lock = threading.Lock()
        self._max_workers = max_workers or self._DEFAULT_MAX_WORKERS

        # Protocol _meta injected on every outbound message after handshake
        self._meta_context: dict[str, Any] = {}

        if auto_start_receiver:
            self.socket_client.start_receiver(self._handle_message)

    def _get_executor(self) -> ThreadPoolExecutor:
        """Lazily build (or rebuild after shutdown) the task worker pool."""
        with self._executor_lock:
            if self._executor is None:
                self._executor = ThreadPoolExecutor(
                    max_workers=self._max_workers,
                    thread_name_prefix="evoto-task",
                )
            return self._executor

    def set_meta_context(self, meta: dict[str, Any]) -> None:
        """
        Attach keys copied into each outgoing _meta (framework use).

        Args:
            meta: e.g. {"plugin_id": "...", "sdk_version": "..."}
        """
        self._meta_context = dict(meta)

    def _build_meta(self, task_id: str = "") -> dict[str, Any]:
        """Merge static meta + timestamp + optional task_id."""
        meta = dict(self._meta_context)
        meta[MetaField.TIMESTAMP] = int(time.time() * 1000)
        if task_id:
            meta[MetaField.TASK_ID] = task_id
        return meta

    def set_task_handler(
        self,
        handler: Callable,
        inline_predicate: Callable[[str], bool] | None = None,
    ) -> None:
        """Register handler for host -> plugin task calls.

        Args:
            handler: ``handler(method, params) -> result``.
            inline_predicate: optional ``predicate(method) -> bool``. When
                it returns True the handler runs synchronously on the
                receiver thread (use for constant-time built-ins like
                ping or for tasks explicitly registered with
                ``inline=True``). Anything else is dispatched onto the
                worker pool so slow tasks can't block ping / events /
                other calls. Defaults to "never inline".
        """
        self._task_handler = handler
        if inline_predicate is not None:
            self._inline_predicate = inline_predicate

    def send_request(self, method: str, params: dict[str, Any], binary_data: bytes = None, task_id: str = "") -> PendingRequest:
        """
        Send JSON-RPC request.

        Args:
            method: host command name
            params: JSON params
            binary_data: optional attachment
            task_id: optional id propagated in _meta
        """
        meta = self._build_meta(task_id)
        message = JsonRpc.create_request(method, params, meta=meta)
        request_id = message[RpcField.ID]

        pr = PendingRequest(request_id)

        with self._lock:
            self._pending[request_id] = pr

        try:
            self.socket_client.send_message(message, binary_data=binary_data)
        except Exception as e:
            with self._lock:
                del self._pending[request_id]
            raise e

        return pr

    def call(self, method: str, params: dict[str, Any], timeout: float = 30.0, binary_data: bytes = None, task_id: str = "") -> Any:
        """Blocking call."""
        pr = self.send_request(method, params, binary_data=binary_data, task_id=task_id)
        return pr.wait(timeout)

    def call_with_callback(
        self,
        method: str,
        params: dict[str, Any],
        callback: Callable[[Any, ReplyStatus], None],
        timeout: float = 30.0,
        binary_data: bytes = None,
        task_id: str = ""
    ) -> str:
        """
        Async call with callback on completion.

        On send failure the callback is invoked instead of raising (single error path).
        """
        meta = self._build_meta(task_id)
        message = JsonRpc.create_request(method, params, meta=meta)
        request_id = message[RpcField.ID]

        pr = PendingRequest(request_id, callback=callback, timeout=timeout)

        with self._lock:
            self._pending[request_id] = pr

        try:
            self.socket_client.send_message(message, binary_data=binary_data)
            pr.start_timeout_timer()
        except Exception as e:
            with self._lock:
                self._pending.pop(request_id, None)
            recv_time = time.time()
            status = ReplyStatus(
                request_id=request_id,
                send_timestamp=pr._send_time,
                recv_timestamp=recv_time,
                elapsed_ms=(recv_time - pr._send_time) * 1000,
                is_timeout=False,
                is_success=False,
                error_code=ApiErrorCode.INTERNAL_ERROR,
                error_message=str(e)
            )
            try:
                callback(None, status)
            except Exception as cb_err:
                logger.error(f"Callback error: {cb_err}", exc_info=True)

        return request_id

    def cancel_request(self, request_id: str) -> bool:
        """Cancel a pending request if still open."""
        with self._lock:
            pr = self._pending.pop(request_id, None)

        if pr and not pr.is_completed:
            pr.set_error(Exception("Request cancelled by user"))
            return True
        return False

    def _handle_message(self, message: dict[str, Any]) -> None:
        """Demultiplex inbound host messages."""
        msg_type = message.get(RpcField.TYPE)

        if msg_type == RpcType.RESPONSE:
            self._handle_response(message)
        elif msg_type == RpcType.REQUEST:
            self._handle_request(message)
        elif msg_type == RpcType.EVENT:
            event_type = message.get(EventField.EVENT, "")
            data = message.get(EventField.DATA, {})
            logger.debug(f"Event received: {event_type} data={data}")
        else:
            logger.debug(f"Unknown message type: {msg_type}")

    def _handle_response(self, message: dict[str, Any]) -> None:
        """Resolve pending request from response."""
        request_id = message.get(RpcField.ID)
        if not request_id:
            return

        with self._lock:
            pr = self._pending.pop(request_id, None)

        if pr:
            if message.get(RpcField.STATUS) == RpcStatus.OK:
                pr.set_result(message.get(RpcField.RESULT))
            else:
                error_data = message.get(RpcField.ERROR, {})
                code = error_data.get(Field.CODE, ApiErrorCode.INTERNAL_ERROR)
                msg = error_data.get(Field.MESSAGE, "Unknown error")
                pr.set_error(ApiError(code, msg))

    def _handle_request(self, message: dict[str, Any]) -> None:
        """Route incoming host request.

        Fast built-ins (ping, shutdown ack, event fan-out) and tasks
        registered with ``inline=True`` run synchronously on the
        receiver thread. Everything else is handed to the worker pool
        so a slow task can't stall ping / events / other calls.
        """
        method = message.get(RpcField.METHOD, "")
        try:
            run_inline = bool(self._inline_predicate(method))
        except Exception as e:
            logger.error(f"Inline predicate error for '{method}': {e}", exc_info=True)
            run_inline = False

        if run_inline:
            self._execute_request(message)
            return

        try:
            self._get_executor().submit(self._execute_request, message)
        except RuntimeError:
            # Pool was shut down concurrently (e.g. during disconnect).
            # Fall back to inline execution so the host still gets a reply.
            logger.warning(
                f"Task pool unavailable for '{method}'; executing inline"
            )
            self._execute_request(message)

    def _execute_request(self, message: dict[str, Any]) -> None:
        """Run host task invocation."""
        request_id = message.get(RpcField.ID)
        method = message.get(RpcField.METHOD)
        params = message.get(RpcField.PARAMS, {})
        incoming_meta = message.get(MetaField.META, {})
        if incoming_meta:
            logger.debug(f"Received _meta from Host: {incoming_meta}")
        binary_data = message.pop(BINARY_DATA_KEY, None)
        if binary_data is not None:
            params[BINARY_DATA_KEY] = binary_data

        meta = self._build_meta()
        incoming_task_id = incoming_meta.get(MetaField.TASK_ID, "")
        if incoming_task_id:
            meta[MetaField.TASK_ID] = incoming_task_id

        if self._task_handler:
            resp_binary = None
            try:
                result = self._task_handler(method, params)
                if isinstance(result, tuple) and len(result) == 2:
                    result, resp_binary = result
                response = JsonRpc.create_response(request_id, result, meta=meta)
            except TaskNotFoundError as e:
                logger.warning(f"Task not found: {e.task_name}")
                response = JsonRpc.create_error(
                    request_id, ApiErrorCode.NOT_FOUND, str(e), meta=meta
                )
            except Exception as e:
                logger.error(f"Task execution error: {e}", exc_info=True)
                response = JsonRpc.create_error(
                    request_id, ApiErrorCode.INTERNAL_ERROR, str(e), meta=meta
                )

            try:
                self.socket_client.send_message(response, binary_data=resp_binary)
            except Exception as e:
                logger.error(f"Failed to send response: {e}")
        else:
            response = JsonRpc.create_error(
                request_id, ApiErrorCode.NOT_FOUND, "No task handler registered", meta=meta
            )
            self.socket_client.send_message(response)

    def cancel_all(self) -> None:
        """Fail all pending requests and tear down the task worker pool."""
        with self._lock:
            pending_copy = list(self._pending.items())
            self._pending.clear()

        for request_id, pr in pending_copy:
            if not pr.is_completed:
                pr.set_error(Exception("Cancelled"))

        # Retire the worker pool. In-flight tasks keep running to
        # completion (wait=False) but no new submissions are accepted;
        # a subsequent reconnect will lazily build a fresh pool.
        with self._executor_lock:
            if self._executor is not None:
                self._executor.shutdown(wait=False)
                self._executor = None

    def ping(self) -> dict[str, Any]:
        """Connectivity check."""
        return self.call(HostCmd.PING, {})

    def log(self, level: str, message: str) -> None:
        """Forward log line to host."""
        self.call(HostCmd.LOG, {LogField.LEVEL: level, LogField.MESSAGE: message})

    def send_event(self, event_type: str, data: dict[str, Any], task_id: str = "") -> None:
        """
        Fire-and-forget event.

        Args:
            event_type: logical name
            data: JSON payload
            task_id: optional correlation id
        """
        message = JsonRpc.create_event(event_type, data, meta=self._build_meta(task_id))
        self.socket_client.send_message(message)
