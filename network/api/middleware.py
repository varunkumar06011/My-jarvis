import time
import json
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from network.security.audit import audit_logger


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id
        return response


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        request_id = request.headers.get("X-Request-ID", "-")
        start = time.time()

        response = await call_next(request)

        duration_ms = (time.time() - start) * 1000

        path = request.url.path
        if not path.startswith("/docs") and not path.startswith("/redoc"):
            audit_logger.log(
                "APIRequest",
                client=client_ip,
                detail=f"{request.method} {path} -> {response.status_code} ({duration_ms:.0f}ms) req_id={request_id}",
            )

        response.headers["X-Response-Time-ms"] = f"{duration_ms:.0f}"
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_size: int = 1024 * 1024):
        super().__init__(app)
        self._max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self._max_body_size:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=413,
                content={
                    "error": "Payload too large",
                    "code": "PAYLOAD_TOO_LARGE",
                    "detail": f"Max body size is {self._max_body_size} bytes",
                },
            )
        return await call_next(request)
