"""Project Context Manager — registers and manages multiple projects,
enabling voice-based project switching and context-aware operations."""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.event_bus import bus
from logs.logger import write_log


PROJECTS_FILE = Path("data/projects.json")
PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)


class Project:
    """Represents a registered project with metadata and context."""

    def __init__(self, name: str, root_path: str, **kwargs):
        self.name = name
        self.root_path = str(Path(root_path).resolve())
        self.github_repo = kwargs.get("github_repo", "")
        self.framework = kwargs.get("framework", "")
        self.language = kwargs.get("language", "")
        self.database = kwargs.get("database", "")
        self.architecture = kwargs.get("architecture", "")
        self.description = kwargs.get("description", "")
        self.tags = kwargs.get("tags", [])
        self.created_at = kwargs.get("created_at", datetime.now().isoformat())
        self.last_accessed = kwargs.get("last_accessed", datetime.now().isoformat())
        self.conversation_count = kwargs.get("conversation_count", 0)
        self.history = kwargs.get("history", [])

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "root_path": self.root_path,
            "github_repo": self.github_repo,
            "framework": self.framework,
            "language": self.language,
            "database": self.database,
            "architecture": self.architecture,
            "description": self.description,
            "tags": self.tags,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "conversation_count": self.conversation_count,
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        return cls(
            name=data.get("name", ""),
            root_path=data.get("root_path", "."),
            github_repo=data.get("github_repo", ""),
            framework=data.get("framework", ""),
            language=data.get("language", ""),
            database=data.get("database", ""),
            architecture=data.get("architecture", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            created_at=data.get("created_at", datetime.now().isoformat()),
            last_accessed=data.get("last_accessed", datetime.now().isoformat()),
            conversation_count=data.get("conversation_count", 0),
            history=data.get("history", []),
        )

    def touch(self):
        self.last_accessed = datetime.now().isoformat()
        self.conversation_count += 1


class ProjectContextManager:
    """Manages multiple registered projects with persistence and voice commands."""

    def __init__(self):
        self._projects: dict[str, Project] = {}
        self._active_project: Optional[str] = None
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if PROJECTS_FILE.exists():
            try:
                data = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
                for item in data.get("projects", []):
                    p = Project.from_dict(item)
                    self._projects[p.name.lower()] = p
                self._active_project = data.get("active_project")
            except Exception:
                pass

    def _save(self):
        with self._lock:
            data = {
                "projects": [p.to_dict() for p in self._projects.values()],
                "active_project": self._active_project,
            }
        PROJECTS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def register(self, name: str, root_path: str, **kwargs) -> Project:
        """Register a new project or update an existing one."""
        project = Project(name, root_path, **kwargs)
        with self._lock:
            self._projects[name.lower()] = project
        self._save()

        bus.publish("ProjectRegistered", {"name": name, "path": root_path})
        write_log("PROJECT_MGR", f"Registered project: {name} at {root_path}")
        return project

    def switch(self, name: str) -> Optional[Project]:
        """Switch to a registered project by name."""
        key = name.lower().strip()
        with self._lock:
            project = self._projects.get(key)
            if project:
                self._active_project = key
                project.touch()
        if project:
            self._save()
            self._reindex_intelligence(project.root_path)
            bus.publish("ProjectSwitched", {"name": project.name, "path": project.root_path})
            write_log("PROJECT_MGR", f"Switched to project: {project.name}")
        return project

    def get_active(self) -> Optional[Project]:
        """Get the currently active project."""
        if not self._active_project:
            return None
        with self._lock:
            return self._projects.get(self._active_project)

    def list_projects(self) -> list[dict]:
        """List all registered projects."""
        with self._lock:
            return [p.to_dict() for p in sorted(self._projects.values(), key=lambda x: x.last_accessed, reverse=True)]

    def get_project(self, name: str) -> Optional[Project]:
        """Get a project by name."""
        with self._lock:
            return self._projects.get(name.lower().strip())

    def remove(self, name: str) -> bool:
        """Remove a project from the registry."""
        key = name.lower().strip()
        with self._lock:
            if key in self._projects:
                del self._projects[key]
                if self._active_project == key:
                    self._active_project = None
            else:
                return False
        self._save()
        bus.publish("ProjectRemoved", {"name": name})
        return True

    def update(self, name: str, **kwargs) -> Optional[Project]:
        """Update project metadata."""
        key = name.lower().strip()
        with self._lock:
            project = self._projects.get(key)
            if not project:
                return None
            for k, v in kwargs.items():
                if hasattr(project, k) and v:
                    setattr(project, k, v)
        self._save()
        return project

    def add_history(self, name: str, entry: str):
        """Add a conversation history entry to a project."""
        key = name.lower().strip()
        with self._lock:
            project = self._projects.get(key)
            if project:
                project.history.append({
                    "timestamp": datetime.now().isoformat(),
                    "entry": entry,
                })
                if len(project.history) > 100:
                    project.history = project.history[-100:]
        self._save()

    def _reindex_intelligence(self, root_path: str):
        """Re-index repository intelligence for the new active project."""
        try:
            from core.service_registry import registry
            if registry.has("repo_intelligence"):
                ri = registry.get("repo_intelligence")
                ri.root = Path(root_path).resolve()
                ri._indexed = False
                ri._cache = None
                ri.analyze_all()
                write_log("PROJECT_MGR", f"Re-indexed repository intelligence for {root_path}")
        except Exception as e:
            write_log("PROJECT_MGR", f"Re-index failed: {e}")

    def auto_detect(self, root_path: str) -> dict:
        """Auto-detect project metadata from the filesystem."""
        root = Path(root_path).resolve()
        info = {"root_path": str(root)}

        # Detect language/framework via repo intelligence if available
        try:
            from core.service_registry import registry
            if registry.has("repo_intelligence"):
                ri = registry.get("repo_intelligence")
                ri.root = root
                ri._indexed = False
                ri._cache = None
                summary = ri.get_summary()
                info["language"] = summary.get("primary_language", "")
                info["framework"] = summary.get("primary_framework", "")
                ks = summary.get("knowledge_summary", {})
                if ks.get("databases"):
                    info["database"] = "detected"
                info["architecture"] = "layered" if summary.get("module_count", 0) > 5 else "simple"
        except Exception:
            pass

        # Detect git
        if (root / ".git").exists():
            info["has_git"] = True
            try:
                import subprocess
                result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    capture_output=True, text=True, timeout=5, cwd=str(root),
                )
                if result.returncode == 0 and result.stdout.strip():
                    remote = result.stdout.strip()
                    if "github.com" in remote:
                        parts = remote.replace(".git", "").split("/")
                        info["github_repo"] = f"{parts[-2]}/{parts[-1]}"
            except Exception:
                pass

        # Detect project name from directory
        info["name"] = root.name

        return info


project_manager = ProjectContextManager()
