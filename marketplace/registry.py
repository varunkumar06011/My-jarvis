import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
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
SANDBOX_DIR = MARKETPLACE_DIR / "sandbox"
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOAD_DIR = MARKETPLACE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

CATEGORIES = ["development", "browser", "office", "ai", "business", "restaurant_pos", "monitoring"]

DANGEROUS_IMPORTS = {"os.system", "subprocess.call", "subprocess.run", "subprocess.Popen",
                     "os.exec", "os.popen", "shutil.rmtree", "shutil.copy", "shutil.move"}
DANGEROUS_PERMISSIONS = {"filesystem_write", "shell_exec", "network_raw", "admin"}


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


class PluginSandbox:
    """Sandbox execution environment for marketplace plugins."""

    def __init__(self, sandbox_root: Path = SANDBOX_DIR):
        self.sandbox_root = sandbox_root
        self.sandbox_root.mkdir(parents=True, exist_ok=True)

    def create_sandbox(self, plugin_name: str) -> Path:
        plugin_sandbox = self.sandbox_root / plugin_name
        plugin_sandbox.mkdir(parents=True, exist_ok=True)
        (plugin_sandbox / "__init__.py").touch()
        return plugin_sandbox

    def destroy_sandbox(self, plugin_name: str):
        plugin_sandbox = self.sandbox_root / plugin_name
        if plugin_sandbox.exists():
            shutil.rmtree(plugin_sandbox, ignore_errors=True)

    def install_to_sandbox(self, plugin_name: str, source_dir: Path = None) -> Path:
        sandbox_path = self.create_sandbox(plugin_name)
        if source_dir and source_dir.exists():
            for f in source_dir.iterdir():
                if f.suffix == ".py" or f.name in ("manifest.json", "README.md", "requirements.txt"):
                    shutil.copy2(f, sandbox_path / f.name)
        return sandbox_path

    def validate_plugin(self, plugin_name: str) -> dict:
        sandbox_path = self.sandbox_root / plugin_name
        if not sandbox_path.exists():
            return {"valid": False, "errors": ["Sandbox directory not found"]}

        errors = []
        warnings = []

        py_files = list(sandbox_path.glob("*.py"))
        if not py_files:
            return {"valid": False, "errors": ["No Python files found"]}

        for py_file in py_files:
            try:
                source = py_file.read_text(encoding="utf-8", errors="replace")
                for dangerous in DANGEROUS_IMPORTS:
                    if dangerous in source:
                        warnings.append(f"{py_file.name}: uses {dangerous}")

                import ast
                tree = ast.parse(source)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        func_name = self._get_call_name(node)
                        if func_name and any(d in func_name for d in DANGEROUS_IMPORTS):
                            errors.append(f"{py_file.name}: dangerous call to {func_name}")
            except Exception as e:
                errors.append(f"{py_file.name}: parse error: {e}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "files": [f.name for f in py_files],
        }

    def _get_call_name(self, node) -> str:
        if isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        elif isinstance(node.func, ast.Name):
            return node.func.id
        return ""

    def run_in_sandbox(self, plugin_name: str, entry_function: str = "run", args: str = "") -> dict:
        sandbox_path = self.sandbox_root / plugin_name
        if not sandbox_path.exists():
            return {"error": "Plugin sandbox not found"}

        validation = self.validate_plugin(plugin_name)
        if not validation["valid"]:
            return {"error": "Plugin failed validation", "details": validation["errors"]}

        try:
            if str(self.sandbox_root) not in sys.path:
                sys.path.insert(0, str(self.sandbox_root))
            module = importlib.import_module(f"{plugin_name}")
            if hasattr(module, entry_function):
                func = getattr(module, entry_function)
                result = func(args) if args else func()
                return {"status": "ok", "result": result}
            return {"error": f"Entry function '{entry_function}' not found"}
        except Exception as e:
            return {"error": f"Execution failed: {e}"}


sandbox = PluginSandbox()


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

            dangerous = [p for p in m.permissions if p in DANGEROUS_PERMISSIONS]
            if dangerous and not m.verified:
                return {"error": "Unverified plugin requests dangerous permissions", "permissions": dangerous}

            install_path = f"plugins/{m.name}"
            sandbox_path = sandbox.install_to_sandbox(m.name)
            validation = sandbox.validate_plugin(m.name)
            if not validation["valid"]:
                sandbox.destroy_sandbox(m.name)
                return {"error": "Plugin failed sandbox validation", "details": validation["errors"]}

            ip = InstalledPlugin(m.id, m.name, m.version, install_path)
            ip.sandbox_path = str(sandbox_path)
            ip.validation = validation
            self._installed[m.name] = ip
            m.downloads += 1

        self._save_installed()
        self._save_registry()
        return {
            "status": "installed",
            "name": m.name,
            "version": m.version,
            "sandbox_path": str(sandbox_path),
            "validation": validation,
        }

    def uninstall(self, name: str) -> dict:
        with self._lock:
            if name in self._installed:
                del self._installed[name]
                sandbox.destroy_sandbox(name)
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
                    sandbox.destroy_sandbox(name)
                    sandbox_path = sandbox.install_to_sandbox(name)
                    validation = sandbox.validate_plugin(name)
                    if not validation["valid"]:
                        return {"error": "Updated plugin failed sandbox validation", "details": validation["errors"]}
                    ip.version = m.version
                    ip.manifest_id = m.id
                    ip.update_available = False
                    ip.sandbox_path = str(sandbox_path)
                    ip.validation = validation
                    self._save_installed()
                    return {"status": "updated", "name": name, "version": m.version, "validation": validation}

        return {"error": "No update available"}

    def list_installed(self) -> list[dict]:
        with self._lock:
            return [ip.to_dict() for ip in self._installed.values()]

    def get_categories(self) -> list[str]:
        return CATEGORIES

    def run_plugin(self, name: str, entry_function: str = "run", args: str = "") -> dict:
        with self._lock:
            ip = self._installed.get(name)
            if not ip:
                return {"error": "Plugin not installed"}
            if not ip.enabled:
                return {"error": "Plugin is disabled"}
        return sandbox.run_in_sandbox(name, entry_function, args)

    def stats(self) -> dict:
        with self._lock:
            return {
                "total_plugins": len(self._registry),
                "total_installed": len(self._installed),
                "verified_plugins": sum(1 for m in self._registry.values() if m.verified),
                "total_downloads": sum(m.downloads for m in self._registry.values()),
                "updates_available": sum(1 for ip in self._installed.values() if ip.update_available),
                "sandboxed_plugins": sum(1 for ip in self._installed.values() if hasattr(ip, 'sandbox_path')),
            }


marketplace = PluginMarketplace()
