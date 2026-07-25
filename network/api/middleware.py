import time
import json

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from network.security.audit import audit_logger


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        start = time.time()

        response = await call_next(request)

        duration_ms = (time.time() - start) * 1000

        # Log API requests (skip static/docs)
        path = request.url.path
        if not path.startswith("/docs") and not path.startswith("/redoc"):
            audit_logger.log(
                "APIRequest",
                client=client_ip,
                detail=f"{request.method} {path} -> {response.status_code} ({duration_ms:.0f}ms)",
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
                content={"error": "Payload too large", "detail": f"Max body size is {self._max_body_size} bytes"},
            )
        return await call_next(request)
