import json
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Optional


LEARNING_DIR = Path("data/learning")
LEARNING_DIR.mkdir(parents=True, exist_ok=True)

PATTERNS_FILE = LEARNING_DIR / "patterns.json"
DECISIONS_FILE = LEARNING_DIR / "decisions.json"
PREFERENCES_FILE = LEARNING_DIR / "preferences.json"


class Pattern:
    def __init__(self, name: str, category: str, pattern: str, solution: str,
                 language: str = "", tags: list[str] = None):
        self.id = f"pat-{int(time.time() * 1000) % 1000000}"
        self.name = name
        self.category = category
        self.pattern = pattern
        self.solution = solution
        self.language = language
        self.tags = tags or []
        self.use_count = 0
        self.success_count = 0
        self.created_at = datetime.now().isoformat()
        self.last_used = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "pattern": self.pattern,
            "solution": self.solution,
            "language": self.language,
            "tags": self.tags,
            "use_count": self.use_count,
            "success_count": self.success_count,
            "success_rate": self.success_count / max(self.use_count, 1),
            "created_at": self.created_at,
            "last_used": self.last_used,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Pattern":
        p = cls(
            name=data.get("name", ""),
            category=data.get("category", ""),
            pattern=data.get("pattern", ""),
            solution=data.get("solution", ""),
            language=data.get("language", ""),
            tags=data.get("tags", []),
        )
        p.id = data.get("id", p.id)
        p.use_count = data.get("use_count", 0)
        p.success_count = data.get("success_count", 0)
        p.created_at = data.get("created_at", p.created_at)
        p.last_used = data.get("last_used")
        return p


class PatternLibrary:
    def __init__(self):
        self._patterns: dict[str, Pattern] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if PATTERNS_FILE.exists():
            try:
                data = json.loads(PATTERNS_FILE.read_text(encoding="utf-8"))
                for item in data:
                    p = Pattern.from_dict(item)
                    self._patterns[p.id] = p
            except Exception:
                pass

    def _save(self):
        with self._lock:
            data = [p.to_dict() for p in self._patterns.values()]
        PATTERNS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def add(self, name: str, category: str, pattern: str, solution: str,
            language: str = "", tags: list[str] = None) -> Pattern:
        p = Pattern(name, category, pattern, solution, language, tags)
        with self._lock:
            self._patterns[p.id] = p
        self._save()
        return p

    def record_use(self, pattern_id: str, success: bool = True):
        with self._lock:
            p = self._patterns.get(pattern_id)
            if p:
                p.use_count += 1
                if success:
                    p.success_count += 1
                p.last_used = datetime.now().isoformat()
        self._save()

    def search(self, query: str = "", category: str = "", language: str = "", limit: int = 20) -> list[dict]:
        results = []
        query_lower = query.lower()

        with self._lock:
            patterns = list(self._patterns.values())

        for p in patterns:
            if category and p.category != category:
                continue
            if language and p.language != language:
                continue
            if query_lower:
                searchable = f"{p.name} {p.pattern} {p.solution} {' '.join(p.tags)}".lower()
                if query_lower not in searchable:
                    continue
            results.append(p.to_dict())

        results.sort(key=lambda x: x.get("use_count", 0), reverse=True)
        return results[:limit]

    def get(self, pattern_id: str) -> Optional[dict]:
        with self._lock:
            p = self._patterns.get(pattern_id)
            return p.to_dict() if p else None

    def categories(self) -> list[str]:
        with self._lock:
            cats = set(p.category for p in self._patterns.values())
        return sorted(cats)

    def stats(self) -> dict:
        with self._lock:
            total = len(self._patterns)
            total_uses = sum(p.use_count for p in self._patterns.values())
            avg_success = sum(p.success_count for p in self._patterns.values()) / max(total_uses, 1)
        return {
            "total_patterns": total,
            "total_uses": total_uses,
            "avg_success_rate": round(avg_success, 2),
            "categories": len(self.categories()),
        }


pattern_library = PatternLibrary()
