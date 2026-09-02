"""Helpers to build JSON-RPC style messages."""

import uuid
from typing import Any

from ..api_fields import RpcField, RpcType, RpcStatus, MetaField, EventField, Field


class JsonRpc:
    """JSON-RPC message builders."""

    @staticmethod
    def create_request(
        method: str,
        params: dict[str, Any],
        request_id: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a request message."""
        msg: dict[str, Any] = {
            RpcField.TYPE: RpcType.REQUEST,
            RpcField.ID: request_id or str(uuid.uuid4()),
            RpcField.METHOD: method,
            RpcField.PARAMS: params
        }
        if meta:
            msg[MetaField.META] = meta
        return msg

    @staticmethod
    def create_response(
        request_id: str,
        result: Any,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a success response."""
        msg: dict[str, Any] = {
            RpcField.TYPE: RpcType.RESPONSE,
            RpcField.ID: request_id,
            RpcField.STATUS: RpcStatus.OK,
            RpcField.RESULT: result
        }
        if meta:
            msg[MetaField.META] = meta
        return msg

    @staticmethod
    def create_error(
        request_id: str,
        code: int,
        message: str,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build an error response."""
        msg: dict[str, Any] = {
            RpcField.TYPE: RpcType.RESPONSE,
            RpcField.ID: request_id,
            RpcField.STATUS: RpcStatus.ERROR,
            RpcField.ERROR: {
                Field.CODE: code,
                Field.MESSAGE: message
            }
        }
        if meta:
            msg[MetaField.META] = meta
        return msg

    @staticmethod
    def create_event(
        event_type: str,
        data: dict[str, Any],
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build an event message."""
        msg: dict[str, Any] = {
            RpcField.TYPE: RpcType.EVENT,
            EventField.EVENT: event_type,
            EventField.DATA: data
        }
        if meta:
            msg[MetaField.META] = meta
        return msg
