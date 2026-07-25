"""Workspace Manager — manages isolated workspaces for multiple projects,
each with its own LLM session, repository intelligence context, and environment."""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.event_bus import bus
from logs.logger import write_log


WORKSPACE_FILE = Path("data/workspaces.json")
WORKSPACE_FILE.parent.mkdir(parents=True, exist_ok=True)


class Workspace:
    """Represents an isolated workspace for a single project."""

    def __init__(self, project_name: str, root_path: str, **kwargs):
        self.project_name = project_name
        self.root_path = str(Path(root_path).resolve())
        self.session_id = kwargs.get("session_id", "")
        self.env_vars = kwargs.get("env_vars", {})
        self.active_branch = kwargs.get("active_branch", "main")
        self.terminal_history = kwargs.get("terminal_history", [])
        self.open_files = kwargs.get("open_files", [])
        self.llm_context = kwargs.get("llm_context", [])
        self.created_at = kwargs.get("created_at", datetime.now().isoformat())
        self.last_active = kwargs.get("last_active", datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "root_path": self.root_path,
            "session_id": self.session_id,
            "env_vars": self.env_vars,
            "active_branch": self.active_branch,
            "terminal_history": self.terminal_history[-50:],
            "open_files": self.open_files,
            "llm_context": self.llm_context[-20:],
            "created_at": self.created_at,
            "last_active": self.last_active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Workspace":
        return cls(
            project_name=data.get("project_name", ""),
            root_path=data.get("root_path", "."),
            session_id=data.get("session_id", ""),
            env_vars=data.get("env_vars", {}),
            active_branch=data.get("active_branch", "main"),
            terminal_history=data.get("terminal_history", []),
            open_files=data.get("open_files", []),
            llm_context=data.get("llm_context", []),
            created_at=data.get("created_at", datetime.now().isoformat()),
            last_active=data.get("last_active", datetime.now().isoformat()),
        )


class WorkspaceManager:
    """Manages multiple isolated workspaces with persistence."""

    def __init__(self):
        self._workspaces: dict[str, Workspace] = {}
        self._active_workspace: Optional[str] = None
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if WORKSPACE_FILE.exists():
            try:
                data = json.loads(WORKSPACE_FILE.read_text(encoding="utf-8"))
                for item in data.get("workspaces", []):
                    ws = Workspace.from_dict(item)
                    self._workspaces[ws.project_name.lower()] = ws
                self._active_workspace = data.get("active_workspace")
            except Exception:
                pass

    def _save(self):
        with self._lock:
            data = {
                "workspaces": [ws.to_dict() for ws in self._workspaces.values()],
                "active_workspace": self._active_workspace,
            }
        WORKSPACE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def create(self, project_name: str, root_path: str, **kwargs) -> Workspace:
        """Create a new workspace for a project."""
        ws = Workspace(project_name, root_path, **kwargs)
        with self._lock:
            self._workspaces[project_name.lower()] = ws
        self._save()

        bus.publish("WorkspaceCreated", {"project": project_name, "path": root_path})
        write_log("WORKSPACE", f"Created workspace for {project_name} at {root_path}")
        return ws

    def switch(self, project_name: str) -> Optional[Workspace]:
        """Switch to a workspace by project name."""
        key = project_name.lower().strip()
        with self._lock:
            ws = self._workspaces.get(key)
            if ws:
                self._active_workspace = key
                ws.last_active = datetime.now().isoformat()
        if ws:
            self._save()
            self._activate_context(ws)
            bus.publish("WorkspaceSwitched", {"project": ws.project_name, "path": ws.root_path})
            write_log("WORKSPACE", f"Switched to workspace: {ws.project_name}")
        return ws

    def get_active(self) -> Optional[Workspace]:
        """Get the currently active workspace."""
        if not self._active_workspace:
            return None
        with self._lock:
            return self._workspaces.get(self._active_workspace)

    def list_workspaces(self) -> list[dict]:
        """List all workspaces."""
        with self._lock:
            return [
                {**ws.to_dict(), "is_active": ws.project_name.lower() == self._active_workspace}
                for ws in sorted(self._workspaces.values(), key=lambda x: x.last_active, reverse=True)
            ]

    def get(self, project_name: str) -> Optional[Workspace]:
        """Get a workspace by project name."""
        with self._lock:
            return self._workspaces.get(project_name.lower().strip())

    def remove(self, project_name: str) -> bool:
        """Remove a workspace."""
        key = project_name.lower().strip()
        with self._lock:
            if key in self._workspaces:
                del self._workspaces[key]
                if self._active_workspace == key:
                    self._active_workspace = None
            else:
                return False
        self._save()
        bus.publish("WorkspaceRemoved", {"project": project_name})
        return True

    def add_llm_context(self, project_name: str, role: str, content: str):
        """Add an LLM context entry to a workspace."""
        key = project_name.lower().strip()
        with self._lock:
            ws = self._workspaces.get(key)
            if ws:
                ws.llm_context.append({
                    "role": role,
                    "content": content[:1000],
                    "timestamp": datetime.now().isoformat(),
                })
                if len(ws.llm_context) > 20:
                    ws.llm_context = ws.llm_context[-20:]
        self._save()

    def get_llm_context(self, project_name: str) -> list:
        """Get LLM context for a workspace."""
        key = project_name.lower().strip()
        with self._lock:
            ws = self._workspaces.get(key)
            if ws:
                return ws.llm_context.copy()
        return []

    def add_terminal_command(self, project_name: str, command: str, output: str = ""):
        """Add a terminal command to workspace history."""
        key = project_name.lower().strip()
        with self._lock:
            ws = self._workspaces.get(key)
            if ws:
                ws.terminal_history.append({
                    "command": command,
                    "output": output[:500],
                    "timestamp": datetime.now().isoformat(),
                })
                if len(ws.terminal_history) > 50:
                    ws.terminal_history = ws.terminal_history[-50:]
        self._save()

    def set_env_var(self, project_name: str, key: str, value: str):
        """Set an environment variable for a workspace."""
        name_key = project_name.lower().strip()
        with self._lock:
            ws = self._workspaces.get(name_key)
            if ws:
                ws.env_vars[key] = value
        self._save()

    def _activate_context(self, ws: Workspace):
        """Activate the workspace context — re-index repo intelligence and
        restore LLM session."""
        try:
            from core.service_registry import registry
            if registry.has("repo_intelligence"):
                ri = registry.get("repo_intelligence")
                ri.root = Path(ws.root_path).resolve()
                ri._indexed = False
                ri._cache = None
                ri.analyze_all()
                write_log("WORKSPACE", f"Re-indexed repo intelligence for {ws.project_name}")
        except Exception as e:
            write_log("WORKSPACE", f"Context activation failed: {e}")

    def sync_with_project_manager(self):
        """Sync workspaces with the project manager — create workspaces for
        registered projects that don't have one yet."""
        try:
            from services.project_manager import project_manager
            for p in project_manager.list_projects():
                if not self.get(p["name"]):
                    self.create(p["name"], p["root_path"])
                    write_log("WORKSPACE", f"Auto-created workspace for {p['name']}")
        except Exception as e:
            write_log("WORKSPACE", f"Sync failed: {e}")


workspace_manager = WorkspaceManager()
