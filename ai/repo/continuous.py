"""Continuous Repository Intelligence — background indexer that periodically
re-analyzes the active repository and publishes events when changes are detected."""

import hashlib
import threading
import time
from pathlib import Path
from typing import Optional

from core.event_bus import bus
from logs.logger import write_log


class ContinuousRepoIntelligence:
    """Runs a background thread that periodically re-indexes the repository,
    detects file changes, and publishes events for the event bus."""

    def __init__(self, interval_seconds: int = 60):
        self.interval = interval_seconds
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._file_hashes: dict[str, str] = {}
        self._last_summary: dict = {}
        self._root: Optional[Path] = None

    def start(self, root: str = "."):
        """Start the continuous indexing thread."""
        if self._running:
            return
        self._root = Path(root).resolve()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="ContinuousRepoIntel")
        self._thread.start()
        write_log("REPO_INTEL", f"Continuous indexing started for {self._root} (interval: {self.interval}s)")
        bus.publish("ContinuousRepoIntelligenceStarted", {"root": str(self._root), "interval": self.interval})

    def stop(self):
        """Stop the continuous indexing thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        write_log("REPO_INTEL", "Continuous indexing stopped")
        bus.publish("ContinuousRepoIntelligenceStopped", {})

    def _loop(self):
        while self._running:
            try:
                self._scan()
            except Exception as e:
                write_log("REPO_INTEL", f"Scan error: {e}")
            time.sleep(self.interval)

    def _scan(self):
        """Scan the repository for changes and re-index if needed."""
        if not self._root or not self._root.exists():
            return

        changed_files = []
        new_files = []
        deleted_files = []

        current_files = {}

        # Scan all source files
        for ext in ("*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.java", "*.go", "*.rs", "*.c", "*.cpp", "*.h"):
            for f in self._root.rglob(ext):
                if any(part in EXCLUDE_DIRS for part in f.parts):
                    continue
                try:
                    content = f.read_bytes()
                    file_hash = hashlib.md5(content).hexdigest()
                    rel = str(f.relative_to(self._root))
                    current_files[rel] = file_hash

                    if rel in self._file_hashes:
                        if self._file_hashes[rel] != file_hash:
                            changed_files.append(rel)
                    else:
                        new_files.append(rel)
                except Exception:
                    continue

        # Detect deleted files
        for old_file in self._file_hashes:
            if old_file not in current_files:
                deleted_files.append(old_file)

        self._file_hashes = current_files

        has_changes = bool(changed_files or new_files or deleted_files)

        if has_changes:
            bus.publish("RepositoryChanged", {
                "new_files": new_files[:50],
                "changed_files": changed_files[:50],
                "deleted_files": deleted_files[:50],
                "total_new": len(new_files),
                "total_changed": len(changed_files),
                "total_deleted": len(deleted_files),
            })
            write_log("REPO_INTEL", f"Changes detected: +{len(new_files)} ~{len(changed_files)} -{len(deleted_files)}")

            # Re-index repository intelligence
            self._reindex()

        # Always publish heartbeat
        bus.publish("RepositoryScanCompleted", {
            "total_files": len(current_files),
            "changes_detected": has_changes,
        })

    def _reindex(self):
        """Trigger re-indexing of repository intelligence and knowledge engine."""
        try:
            from core.service_registry import registry
            if registry.has("repo_intelligence"):
                ri = registry.get("repo_intelligence")
                ri._indexed = False
                ri._cache = None
                ri.analyze_all()
                write_log("REPO_INTEL", "Repository intelligence re-indexed")

            if registry.has("knowledge_engine"):
                ke = registry.get("knowledge_engine")
                ke.indexer.index()
                write_log("REPO_INTEL", "Knowledge engine re-indexed")
        except Exception as e:
            write_log("REPO_INTEL", f"Re-index failed: {e}")

    def get_status(self) -> dict:
        """Get current status of the continuous indexer."""
        return {
            "running": self._running,
            "root": str(self._root) if self._root else None,
            "interval": self.interval,
            "tracked_files": len(self._file_hashes),
            "last_summary": self._last_summary,
        }


EXCLUDE_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", ".idea",
    ".vscode", "dist", "build", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", "htmlcov", ".eggs", ".tox", "env",
}


continuous_repo_intelligence = ContinuousRepoIntelligence()
