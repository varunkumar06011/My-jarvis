import hashlib
import os
import time
from pathlib import Path
from typing import Optional
from collections import defaultdict

from core.event_bus import bus
from ai.knowledge.indexer import knowledge_indexer, IndexEntry


class IncrementalIndexer:
    """Handles incremental indexing, real-time updates, version awareness,
    and file change detection for the knowledge index."""

    def __init__(self):
        self._file_index: dict[str, dict] = {}
        self._watching: dict[str, Path] = {}
        self._change_log: list[dict] = []
        self._lock = False

    def register_repo(self, root: str, repo_name: str = None):
        """Register a repository for incremental indexing."""
        root_path = Path(root).resolve()
        repo_name = repo_name or root_path.name
        self._watching[repo_name] = root_path
        self._scan_files(repo_name, root_path)

        bus.publish("IncrementalIndexRegistered", {"repo": repo_name, "root": str(root_path)})
        return {"repo": repo_name, "files_tracked": len(self._file_index.get(repo_name, {}))}

    def _scan_files(self, repo_name: str, root: Path):
        if repo_name not in self._file_index:
            self._file_index[repo_name] = {}

        for filepath in root.rglob("*"):
            if not filepath.is_file():
                continue
            if any(part in {"venv", "__pycache__", ".git", "node_modules", "dist", "build"} for part in filepath.parts):
                continue

            rel = str(filepath.relative_to(root)).replace("\\", "/")
            try:
                stat = filepath.stat()
                content = filepath.read_text(encoding="utf-8", errors="replace")
                file_hash = hashlib.md5(content.encode()).hexdigest()

                self._file_index[repo_name][rel] = {
                    "hash": file_hash,
                    "mtime": stat.st_mtime,
                    "size": stat.st_size,
                }
            except Exception:
                pass

    def detect_changes(self, repo_name: str = None) -> dict:
        """Detect changed, added, and removed files since last scan."""
        all_changes = {"added": [], "modified": [], "removed": []}

        repos_to_check = [repo_name] if repo_name else list(self._watching.keys())

        for rn in repos_to_check:
            if rn not in self._watching:
                continue

            root = self._watching[rn]
            current_files = {}

            for filepath in root.rglob("*"):
                if not filepath.is_file():
                    continue
                if any(part in {"venv", "__pycache__", ".git", "node_modules", "dist", "build"} for part in filepath.parts):
                    continue

                rel = str(filepath.relative_to(root)).replace("\\", "/")
                try:
                    stat = filepath.stat()
                    content = filepath.read_text(encoding="utf-8", errors="replace")
                    file_hash = hashlib.md5(content.encode()).hexdigest()
                    current_files[rel] = {"hash": file_hash, "mtime": stat.st_mtime, "size": stat.st_size}
                except Exception:
                    pass

            previous = self._file_index.get(rn, {})

            for rel, info in current_files.items():
                if rel not in previous:
                    all_changes["added"].append({"repo": rn, "file": rel})
                elif previous[rel]["hash"] != info["hash"]:
                    all_changes["modified"].append({"repo": rn, "file": rel, "old_hash": previous[rel]["hash"], "new_hash": info["hash"]})

            for rel in previous:
                if rel not in current_files:
                    all_changes["removed"].append({"repo": rn, "file": rel})

            self._file_index[rn] = current_files

        if any(all_changes.values()):
            self._change_log.append({
                "timestamp": time.time(),
                "added": len(all_changes["added"]),
                "modified": len(all_changes["modified"]),
                "removed": len(all_changes["removed"]),
            })
            if len(self._change_log) > 500:
                self._change_log = self._change_log[-500:]

            bus.publish("IncrementalChangesDetected", all_changes)

        return all_changes

    def update_incremental(self, repo_name: str = None) -> dict:
        """Detect changes and re-index only modified files."""
        changes = self.detect_changes(repo_name)

        reindexed = 0
        removed = 0

        for change in changes["added"] + changes["modified"]:
            rn = change["repo"]
            root = self._watching.get(rn)
            if root is None:
                continue

            filepath = root / change["file"]
            if not filepath.exists():
                continue

            ext = filepath.suffix.lower()
            if ext not in knowledge_indexer.INDEXABLE_EXTENSIONS:
                continue

            language = knowledge_indexer.INDEXABLE_EXTENSIONS[ext]

            try:
                content = filepath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            knowledge_indexer._entries = [
                e for e in knowledge_indexer._entries
                if not (e.repo == rn and e.file == change["file"])
            ]

            chunks = knowledge_indexer._chunk_content(content, language)
            for chunk in chunks:
                entry = IndexEntry(
                    repo=rn,
                    file=change["file"],
                    language=language,
                    content=chunk["content"],
                    chunk_type=chunk["type"],
                    line_start=chunk["line_start"],
                    line_end=chunk["line_end"],
                    symbols=chunk.get("symbols", []),
                )
                knowledge_indexer._entries.append(entry)
                reindexed += 1

        for change in changes["removed"]:
            rn = change["repo"]
            before = len(knowledge_indexer._entries)
            knowledge_indexer._entries = [
                e for e in knowledge_indexer._entries
                if not (e.repo == rn and e.file == change["file"])
            ]
            removed += before - len(knowledge_indexer._entries)

        bus.publish("IncrementalIndexUpdated", {
            "reindexed_chunks": reindexed,
            "removed_chunks": removed,
        })

        return {
            "reindexed_files": len(changes["added"]) + len(changes["modified"]),
            "removed_files": len(changes["removed"]),
            "reindexed_chunks": reindexed,
            "removed_chunks": removed,
        }

    def get_file_version(self, repo_name: str, file_path: str) -> Optional[dict]:
        """Get the current indexed version of a file."""
        return self._file_index.get(repo_name, {}).get(file_path)

    def get_change_log(self, limit: int = 50) -> list:
        return list(reversed(self._change_log[-limit:]))

    def list_watched_repos(self) -> list:
        return list(self._watching.keys())


incremental_indexer = IncrementalIndexer()
