import json
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


SYNC_DIR = Path("data/sync")
SYNC_DIR.mkdir(parents=True, exist_ok=True)

DEVICES_FILE = SYNC_DIR / "devices.json"
SYNC_LOG_FILE = SYNC_DIR / "sync_log.json"


class DeviceInfo:
    def __init__(self, name: str, device_type: str, platform: str):
        self.id = uuid.uuid4().hex[:12]
        self.name = name
        self.device_type = device_type  # desktop, android, ios, web
        self.platform = platform
        self.registered_at = datetime.now().isoformat()
        self.last_seen = self.registered_at
        self.sync_version = 0
        self.capabilities = []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "device_type": self.device_type,
            "platform": self.platform,
            "registered_at": self.registered_at,
            "last_seen": self.last_seen,
            "sync_version": self.sync_version,
            "capabilities": self.capabilities,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DeviceInfo":
        d = cls(data.get("name", ""), data.get("device_type", ""), data.get("platform", ""))
        d.id = data.get("id", d.id)
        d.registered_at = data.get("registered_at", d.registered_at)
        d.last_seen = data.get("last_seen", d.last_seen)
        d.sync_version = data.get("sync_version", 0)
        d.capabilities = data.get("capabilities", [])
        return d


class SyncPayload:
    def __init__(self, device_id: str, data_type: str, payload: dict, version: int = 0):
        self.id = uuid.uuid4().hex[:12]
        self.device_id = device_id
        self.data_type = data_type  # chat, settings, preferences, automation
        self.payload = payload
        self.version = version
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "device_id": self.device_id,
            "data_type": self.data_type,
            "payload": self.payload,
            "version": self.version,
            "timestamp": self.timestamp,
        }


class SyncManager:
    def __init__(self):
        self._devices: dict[str, DeviceInfo] = {}
        self._sync_log: list[dict] = []
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if DEVICES_FILE.exists():
            try:
                data = json.loads(DEVICES_FILE.read_text(encoding="utf-8"))
                for item in data:
                    d = DeviceInfo.from_dict(item)
                    self._devices[d.id] = d
            except Exception:
                pass

        if SYNC_LOG_FILE.exists():
            try:
                self._sync_log = json.loads(SYNC_LOG_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass

    def _save_devices(self):
        with self._lock:
            data = [d.to_dict() for d in self._devices.values()]
        DEVICES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _save_log(self):
        with self._lock:
            SYNC_LOG_FILE.write_text(json.dumps(self._sync_log[-200:], indent=2, ensure_ascii=False), encoding="utf-8")

    def register_device(self, name: str, device_type: str, platform: str,
                        capabilities: list[str] = None) -> DeviceInfo:
        d = DeviceInfo(name, device_type, platform)
        if capabilities:
            d.capabilities = capabilities
        with self._lock:
            self._devices[d.id] = d
        self._save_devices()
        self._log_sync("register", d.id, f"Registered {name} ({device_type})")
        return d

    def heartbeat(self, device_id: str) -> bool:
        with self._lock:
            d = self._devices.get(device_id)
            if d:
                d.last_seen = datetime.now().isoformat()
                self._save_devices()
                return True
        return False

    def push(self, device_id: str, data_type: str, payload: dict) -> SyncPayload:
        with self._lock:
            d = self._devices.get(device_id)
            if d:
                d.sync_version += 1
                version = d.sync_version
            else:
                version = 0

        sp = SyncPayload(device_id, data_type, payload, version)
        self._log_sync("push", device_id, f"Pushed {data_type} v{version}")
        return sp

    def pull(self, device_id: str, since_version: int = 0) -> list[dict]:
        results = []
        with self._lock:
            for entry in self._sync_log:
                if entry.get("device_id") == device_id and entry.get("version", 0) > since_version:
                    results.append(entry)
        return results

    def list_devices(self) -> list[dict]:
        with self._lock:
            return [d.to_dict() for d in self._devices.values()]

    def remove_device(self, device_id: str) -> bool:
        with self._lock:
            if device_id in self._devices:
                del self._devices[device_id]
                self._save_devices()
                self._log_sync("remove", device_id, "Device removed")
                return True
        return False

    def _log_sync(self, action: str, device_id: str, message: str):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "device_id": device_id,
            "message": message,
        }
        with self._lock:
            self._sync_log.append(entry)
            if len(self._sync_log) > 200:
                self._sync_log = self._sync_log[-200:]
        self._save_log()

    def get_sync_log(self, limit: int = 50) -> list[dict]:
        with self._lock:
            return list(reversed(self._sync_log[-limit:]))

    def stats(self) -> dict:
        with self._lock:
            return {
                "total_devices": len(self._devices),
                "by_type": {t: sum(1 for d in self._devices.values() if d.device_type == t)
                           for t in set(d.device_type for d in self._devices.values())},
                "total_syncs": len(self._sync_log),
            }


sync_manager = SyncManager()
