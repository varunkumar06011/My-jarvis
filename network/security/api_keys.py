import hashlib
import json
import os
import secrets
from pathlib import Path
from typing import Optional

KEYS_FILE = Path("data/api_keys.json")


class APIKeyManager:
    def __init__(self):
        self._keys: dict[str, dict] = {}
        self._load()

    def _load(self):
        if KEYS_FILE.exists():
            try:
                with open(KEYS_FILE, "r", encoding="utf-8") as f:
                    self._keys = json.load(f)
            except Exception:
                self._keys = {}
        else:
            self._keys = {}

    def _save(self):
        KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(self._keys, f, indent=2, ensure_ascii=False)

    def generate_key(self, name: str, permissions: list[str] | None = None) -> str:
        raw_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        self._keys[key_hash] = {
            "name": name,
            "permissions": permissions or ["read", "chat"],
            "active": True,
        }
        self._save()
        return raw_key

    def validate(self, raw_key: str) -> bool:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        entry = self._keys.get(key_hash)
        return entry is not None and entry.get("active", False)

    def get_permissions(self, raw_key: str) -> list[str]:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        entry = self._keys.get(key_hash)
        if entry is None:
            return []
        return entry.get("permissions", [])

    def get_name(self, raw_key: str) -> Optional[str]:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        entry = self._keys.get(key_hash)
        if entry is None:
            return None
        return entry.get("name")

    def revoke(self, raw_key: str) -> bool:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        if key_hash in self._keys:
            self._keys[key_hash]["active"] = False
            self._save()
            return True
        return False

    def list_keys(self) -> list[dict]:
        result = []
        for key_hash, info in self._keys.items():
            result.append({
                "name": info.get("name"),
                "permissions": info.get("permissions", []),
                "active": info.get("active", False),
                "key_hash": key_hash[:12] + "...",
            })
        return result


api_key_manager = APIKeyManager()
