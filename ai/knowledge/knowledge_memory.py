import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from collections import defaultdict

from core.event_bus import bus

KNOWLEDGE_MEMORY_DIR = Path("data/knowledge_memory")
KNOWLEDGE_MEMORY_DIR.mkdir(parents=True, exist_ok=True)

KNOWLEDGE_MEMORY_FILE = KNOWLEDGE_MEMORY_DIR / "memory.json"


class KnowledgeMemory:
    """Persists conversations, decisions, architecture notes,
    previous bug fixes, and design discussions for long-term recall."""

    ENTRY_TYPES = {
        "conversation": "Conversation history",
        "decision": "Architecture/technical decision",
        "architecture_note": "Architecture note",
        "bug_fix": "Previous bug fix",
        "design_discussion": "Design discussion",
        "code_pattern": "Discovered code pattern",
        "lesson_learned": "Lesson learned from failure",
    }

    def __init__(self):
        self._entries: list[dict] = []
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if KNOWLEDGE_MEMORY_FILE.exists():
            try:
                self._entries = json.loads(KNOWLEDGE_MEMORY_FILE.read_text(encoding="utf-8"))
            except Exception:
                self._entries = []

    def _save(self):
        with self._lock:
            KNOWLEDGE_MEMORY_FILE.write_text(
                json.dumps(self._entries, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )

    def store(self, entry_type: str, title: str, content: str,
              metadata: dict = None, tags: list = None,
              repo: str = None) -> dict:
        """Store a knowledge memory entry."""
        if entry_type not in self.ENTRY_TYPES:
            return {"error": f"Invalid entry type. Valid types: {list(self.ENTRY_TYPES.keys())}"}

        entry = {
            "id": f"km-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(self._entries)}",
            "type": entry_type,
            "title": title,
            "content": content,
            "metadata": metadata or {},
            "tags": tags or [],
            "repo": repo,
            "created_at": datetime.now().isoformat(),
            "timestamp": time.time(),
        }

        with self._lock:
            self._entries.append(entry)
        self._save()

        bus.publish("KnowledgeMemoryStored", {"id": entry["id"], "type": entry_type, "title": title})

        return entry

    def search(self, query: str = None, entry_type: str = None,
               tags: list = None, repo: str = None, limit: int = 20) -> list:
        """Search knowledge memory entries."""
        with self._lock:
            entries = list(self._entries)

        results = []
        query_lower = query.lower() if query else ""

        for entry in entries:
            if entry_type and entry["type"] != entry_type:
                continue
            if repo and entry.get("repo") != repo:
                continue
            if tags:
                entry_tags = set(entry.get("tags", []))
                if not set(tags).intersection(entry_tags):
                    continue
            if query_lower:
                searchable = f"{entry['title']} {entry['content']} {entry.get('metadata', {})}".lower()
                if query_lower not in searchable:
                    continue
            results.append(entry)

        results.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return results[:limit]

    def get(self, entry_id: str) -> Optional[dict]:
        with self._lock:
            for entry in self._entries:
                if entry["id"] == entry_id:
                    return entry
        return None

    def update(self, entry_id: str, content: str = None, tags: list = None,
               metadata: dict = None) -> Optional[dict]:
        with self._lock:
            for entry in self._entries:
                if entry["id"] == entry_id:
                    if content is not None:
                        entry["content"] = content
                    if tags is not None:
                        entry["tags"] = tags
                    if metadata is not None:
                        entry["metadata"] = {**entry.get("metadata", {}), **metadata}
                    entry["updated_at"] = datetime.now().isoformat()
                    self._save()
                    return entry
        return None

    def delete(self, entry_id: str) -> bool:
        with self._lock:
            before = len(self._entries)
            self._entries = [e for e in self._entries if e["id"] != entry_id]
            if len(self._entries) < before:
                self._save()
                return True
        return False

    def stats(self) -> dict:
        with self._lock:
            total = len(self._entries)
        by_type = defaultdict(int)
        by_repo = defaultdict(int)

        for entry in self._entries:
            by_type[entry["type"]] += 1
            if entry.get("repo"):
                by_repo[entry["repo"]] += 1

        return {
            "total_entries": total,
            "by_type": dict(by_type),
            "by_repo": dict(by_repo),
            "entry_types": self.ENTRY_TYPES,
        }

    def get_conversations(self, limit: int = 20) -> list:
        return self.search(entry_type="conversation", limit=limit)

    def get_decisions(self, limit: int = 20) -> list:
        return self.search(entry_type="decision", limit=limit)

    def get_bug_fixes(self, limit: int = 20) -> list:
        return self.search(entry_type="bug_fix", limit=limit)

    def get_architecture_notes(self, limit: int = 20) -> list:
        return self.search(entry_type="architecture_note", limit=limit)


knowledge_memory = KnowledgeMemory()
