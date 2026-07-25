import hashlib
import hmac
import json
import time
from typing import Optional

from configs.config import API_JWT_SECRET, API_JWT_EXPIRE_SECONDS


class JWTManager:
    def __init__(self, secret: str = API_JWT_SECRET, expire_seconds: int = API_JWT_EXPIRE_SECONDS):
        self._secret = secret.encode("utf-8")
        self._expire_seconds = expire_seconds

    def _b64_encode(self, data: bytes) -> str:
        import base64
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

    def _b64_decode(self, data: str) -> bytes:
        import base64
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data)

    def _sign(self, data: str) -> str:
        sig = hmac.new(self._secret, data.encode("utf-8"), hashlib.sha256).digest()
        return self._b64_encode(sig)

    def create_token(self, subject: str, permissions: list[str] | None = None) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        now = int(time.time())
        payload = {
            "sub": subject,
            "permissions": permissions or [],
            "iat": now,
            "exp": now + self._expire_seconds,
        }

        header_b64 = self._b64_encode(json.dumps(header, separators=(",", ":")).encode())
        payload_b64 = self._b64_encode(json.dumps(payload, separators=(",", ":")).encode())

        signing_input = f"{header_b64}.{payload_b64}"
        signature = self._sign(signing_input)

        return f"{signing_input}.{signature}"

    def verify_token(self, token: str) -> Optional[dict]:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None

            header_b64, payload_b64, signature = parts
            signing_input = f"{header_b64}.{payload_b64}"
            expected_sig = self._sign(signing_input)

            if not hmac.compare_digest(signature, expected_sig):
                return None

            payload = json.loads(self._b64_decode(payload_b64))

            if payload.get("exp", 0) < int(time.time()):
                return None

            return payload
        except Exception:
            return None

    def refresh_token(self, token: str) -> Optional[str]:
        payload = self.verify_token(token)
        if payload is None:
            return None
        return self.create_token(payload["sub"], payload.get("permissions", []))


jwt_manager = JWTManager()
