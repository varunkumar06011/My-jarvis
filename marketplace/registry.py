import json
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


MARKETPLACE_DIR = Path("data/marketplace")
MARKETPLACE_DIR.mkdir(parents=True, exist_ok=True)

REGISTRY_FILE = MARKETPLACE_DIR / "registry.json"
INSTALLED_FILE = MARKETPLACE_DIR / "installed.json"

CATEGORIES = ["development", "browser", "office", "ai", "business", "restaurant_pos", "monitoring"]


class PluginManifest:
    def __init__(self, name: str, version: str, category: str, description: str,
                 author: str = "", homepage: str = "", dependencies: list[str] = None,
                 permissions: list[str] = None, min_app_version: str = "1.0",
                 signature: str = "", checksum: str = ""):
        self.id = uuid.uuid4().hex[:12]
        self.name = name
        self.version = version
        self.category = category
        self.description = description
        self.author = author
        self.homepage = homepage
        self.dependencies = dependencies or []
        self.permissions = permissions or []
        self.min_app_version = min_app_version
        self.signature = signature
        self.checksum = checksum
        self.created_at = datetime.now().isoformat()
        self.downloads = 0
        self.rating = 0.0
        self.verified = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "category": self.category,
            "description": self.description,
            "author": self.author,
            "homepage": self.homepage,
            "dependencies": self.dependencies,
            "permissions": self.permissions,
            "min_app_version": self.min_app_version,
            "signature": self.signature,
            "checksum": self.checksum,
            "created_at": self.created_at,
            "downloads": self.downloads,
            "rating": self.rating,
            "verified": self.verified,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PluginManifest":
        m = cls(
            name=data.get("name", ""),
            version=data.get("version", ""),
            category=data.get("category", ""),
            description=data.get("description", ""),
            author=data.get("author", ""),
            homepage=data.get("homepage", ""),
            dependencies=data.get("dependencies", []),
            permissions=data.get("permissions", []),
            min_app_version=data.get("min_app_version", "1.0"),
            signature=data.get("signature", ""),
            checksum=data.get("checksum", ""),
        )
        m.id = data.get("id", m.id)
        m.created_at = data.get("created_at", m.created_at)
        m.downloads = data.get("downloads", 0)
        m.rating = data.get("rating", 0.0)
        m.verified = data.get("verified", False)
        return m


class InstalledPlugin:
    def __init__(self, manifest_id: str, name: str, version: str, install_path: str):
        self.manifest_id = manifest_id
        self.name = name
        self.version = version
        self.install_path = install_path
        self.installed_at = datetime.now().isoformat()
        self.enabled = True
        self.update_available = False

    def to_dict(self) -> dict:
        return {
            "manifest_id": self.manifest_id,
            "name": self.name,
            "version": self.version,
            "install_path": self.install_path,
            "installed_at": self.installed_at,
            "enabled": self.enabled,
            "update_available": self.update_available,
        }


class PluginMarketplace:
    def __init__(self):
        self._registry: dict[str, PluginManifest] = {}
        self._installed: dict[str, InstalledPlugin] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if REGISTRY_FILE.exists():
            try:
                data = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
                for item in data:
                    m = PluginManifest.from_dict(item)
                    self._registry[m.id] = m
            except Exception:
                pass

        if INSTALLED_FILE.exists():
            try:
                data = json.loads(INSTALLED_FILE.read_text(encoding="utf-8"))
                for item in data:
                    ip = InstalledPlugin(item.get("manifest_id", ""), item.get("name", ""),
                                         item.get("version", ""), item.get("install_path", ""))
                    ip.installed_at = item.get("installed_at", ip.installed_at)
                    ip.enabled = item.get("enabled", True)
                    ip.update_available = item.get("update_available", False)
                    self._installed[ip.name] = ip
            except Exception:
                pass

    def _save_registry(self):
        with self._lock:
            data = [m.to_dict() for m in self._registry.values()]
        REGISTRY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _save_installed(self):
        with self._lock:
            data = [ip.to_dict() for ip in self._installed.values()]
        INSTALLED_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def publish(self, name: str, version: str, category: str, description: str,
                author: str = "", dependencies: list[str] = None,
                permissions: list[str] = None, signature: str = "",
                checksum: str = "") -> PluginManifest:
        m = PluginManifest(name, version, category, description, author,
                           dependencies=dependencies, permissions=permissions,
                           signature=signature, checksum=checksum)
        m.verified = bool(signature)
        with self._lock:
            self._registry[m.id] = m
        self._save_registry()
        return m

    def discover(self, category: str = "", query: str = "", limit: int = 20) -> list[dict]:
        results = []
        query_lower = query.lower()

        with self._lock:
            plugins = list(self._registry.values())

        for p in plugins:
            if category and p.category != category:
                continue
            if query_lower:
                searchable = f"{p.name} {p.description} {p.author}".lower()
                if query_lower not in searchable:
                    continue
            results.append(p.to_dict())

        results.sort(key=lambda x: x.get("downloads", 0), reverse=True)
        return results[:limit]

    def install(self, manifest_id: str) -> dict:
        with self._lock:
            m = self._registry.get(manifest_id)
            if not m:
                return {"error": "Plugin not found in registry"}

            if m.name in self._installed:
                return {"error": "Plugin already installed", "name": m.name}

            deps_ok = all(dep in self._installed for dep in m.dependencies)
            if not deps_ok:
                missing = [d for d in m.dependencies if d not in self._installed]
                return {"error": "Missing dependencies", "missing": missing}

            install_path = f"plugins/{m.name}"
            ip = InstalledPlugin(m.id, m.name, m.version, install_path)
            self._installed[m.name] = ip
            m.downloads += 1

        self._save_installed()
        self._save_registry()
        return {"status": "installed", "name": m.name, "version": m.version}

    def uninstall(self, name: str) -> dict:
        with self._lock:
            if name in self._installed:
                del self._installed[name]
                self._save_installed()
                return {"status": "uninstalled", "name": name}
        return {"error": "Plugin not installed"}

    def enable(self, name: str) -> dict:
        with self._lock:
            ip = self._installed.get(name)
            if ip:
                ip.enabled = True
                self._save_installed()
                return {"status": "enabled", "name": name}
        return {"error": "Plugin not found"}

    def disable(self, name: str) -> dict:
        with self._lock:
            ip = self._installed.get(name)
            if ip:
                ip.enabled = False
                self._save_installed()
                return {"status": "disabled", "name": name}
        return {"error": "Plugin not found"}

    def check_updates(self) -> list[dict]:
        updates = []
        with self._lock:
            for name, ip in self._installed.items():
                for m in self._registry.values():
                    if m.name == name and m.version != ip.version:
                        ip.update_available = True
                        updates.append({
                            "name": name,
                            "current": ip.version,
                            "available": m.version,
                            "manifest_id": m.id,
                        })
                        break
                    else:
                        ip.update_available = False
        self._save_installed()
        return updates

    def update(self, name: str) -> dict:
        with self._lock:
            ip = self._installed.get(name)
            if not ip:
                return {"error": "Plugin not installed"}

            for m in self._registry.values():
                if m.name == name and m.version != ip.version:
                    ip.version = m.version
                    ip.manifest_id = m.id
                    ip.update_available = False
                    self._save_installed()
                    return {"status": "updated", "name": name, "version": m.version}

        return {"error": "No update available"}

    def list_installed(self) -> list[dict]:
        with self._lock:
            return [ip.to_dict() for ip in self._installed.values()]

    def get_categories(self) -> list[str]:
        return CATEGORIES

    def stats(self) -> dict:
        with self._lock:
            return {
                "total_plugins": len(self._registry),
                "total_installed": len(self._installed),
                "verified_plugins": sum(1 for m in self._registry.values() if m.verified),
                "total_downloads": sum(m.downloads for m in self._registry.values()),
                "updates_available": sum(1 for ip in self._installed.values() if ip.update_available),
            }


marketplace = PluginMarketplace()
