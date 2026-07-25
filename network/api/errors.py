from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class ErrorCode(str, Enum):
    # ── Auth ──
    AUTH_MISSING = "AUTH_MISSING"
    AUTH_INVALID = "AUTH_INVALID"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    AUTH_PERMISSION_DENIED = "AUTH_PERMISSION_DENIED"

    # ── Rate limiting ──
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # ── Validation ──
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"

    # ── Services ──
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    SERVICE_NOT_FOUND = "SERVICE_NOT_FOUND"
    SERVICE_TIMEOUT = "SERVICE_TIMEOUT"

    # ── Resources ──
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"

    # ── Internal ──
    INTERNAL_ERROR = "INTERNAL_ERROR"
    BAD_REQUEST = "BAD_REQUEST"

    # ── Restart ──
    RESTART_FAILED = "RESTART_FAILED"


class APIError(BaseModel):
    error: str
    code: ErrorCode
    detail: Optional[Any] = None
    request_id: Optional[str] = None


class APIError(Exception):
    def __init__(self, code: ErrorCode, message: str, detail: Any = None, status_code: int = 400):
        self.code = code
        self.message = message
        self.detail = detail
        self.status_code = status_code
        super().__init__(message)

    def to_response(self, request_id: Optional[str] = None) -> dict:
        return {
            "error": self.message,
            "code": self.code.value,
            "detail": self.detail,
            "request_id": request_id,
        }
