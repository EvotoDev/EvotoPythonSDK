"""Error code constants shared between host and plugin.

HTTP-style semantics for cross-language clarity.
"""


class ApiErrorCode:
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    GONE = 410
    PRECONDITION_FAILED = 412
    INTERNAL_ERROR = 500
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504
