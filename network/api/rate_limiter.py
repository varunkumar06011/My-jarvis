import time
from collections import defaultdict
from threading import Lock
from typing import Optional

from fastapi import HTTPException, Request, status

from configs.config import API_RATE_LIMIT_PER_MINUTE, API_RATE_LIMIT_PER_HOUR


class RateLimiter:
    def __init__(
        self,
        per_minute: int = API_RATE_LIMIT_PER_MINUTE,
        per_hour: int = API_RATE_LIMIT_PER_HOUR,
    ):
        self._per_minute = per_minute
        self._per_hour = per_hour
        self._minute_buckets: dict[str, list[float]] = defaultdict(list)
        self._hour_buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def _prune(self, bucket: list[float], window: float) -> list[float]:
        cutoff = time.time() - window
        return [ts for ts in bucket if ts > cutoff]

    def check(self, client_id: str) -> bool:
        now = time.time()

        with self._lock:
            minute_reqs = self._prune(self._minute_buckets[client_id], 60)
            hour_reqs = self._prune(self._hour_buckets[client_id], 3600)

            if len(minute_reqs) >= self._per_minute:
                return False
            if len(hour_reqs) >= self._per_hour:
                return False

            minute_reqs.append(now)
            hour_reqs.append(now)

            self._minute_buckets[client_id] = minute_reqs
            self._hour_buckets[client_id] = hour_reqs

            return True

    def get_stats(self, client_id: str) -> dict:
        with self._lock:
            minute_count = len(self._prune(self._minute_buckets.get(client_id, []), 60))
            hour_count = len(self._prune(self._hour_buckets.get(client_id, []), 3600))
            return {
                "minute_count": minute_count,
                "minute_limit": self._per_minute,
                "hour_count": hour_count,
                "hour_limit": self._per_hour,
            }


rate_limiter = RateLimiter()


async def enforce_rate_limit(request: Request) -> None:
    from network.api.authentication import authenticate

    # This is called as a dependency alongside authenticate
    # The actual enforcement happens in the middleware
    pass


class RateLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        # Skip docs and health endpoints
        path = scope.get("path", "")
        if path in ("/docs", "/redoc", "/openapi.json", "/api/health"):
            return await self.app(scope, receive, send)

        # Extract client IP as fallback identifier
        client_ip = scope.get("client", ("unknown", 0))[0]

        if not rate_limiter.check(client_ip):
            response = {
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"x-ratelimit-retry", b"60"),
                ],
            }
            await send(response)
            await send({
                "type": "http.response.body",
                "body": b'{"error":"Rate limit exceeded","code":"RATE_LIMIT_EXCEEDED","detail":"Too many requests. Please slow down."}',
            })
            return

        await self.app(scope, receive, send)
