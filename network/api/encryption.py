import base64
import hashlib
import os

from cryptography.fernet import Fernet

from configs.config import API_JWT_SECRET


def _derive_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


class EncryptionManager:
    def __init__(self, secret: str = API_JWT_SECRET):
        self._key = _derive_key(secret)
        self._fernet = Fernet(self._key)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")

    def encrypt_bytes(self, data: bytes) -> bytes:
        return self._fernet.encrypt(data)

    def decrypt_bytes(self, data: bytes) -> bytes:
        return self._fernet.decrypt(data)


encryption_manager = EncryptionManager()
