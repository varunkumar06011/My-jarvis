import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

DECISIONS_FILE = Path("data/decisions.json")


class DecisionRecord:
    def __init__(self, title: str, context: str, decision: str,
                 rationale: str, alternatives: list[str] = None,
                 consequences: str = "", tags: list[str] = None):
        self.id = f"dec-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.title = title
        self.context = context
        self.decision = decision
        self.rationale = rationale
        self.alternatives = alternatives or []
        self.consequences = consequences
        self.tags = tags or []
        self.created_at = datetime.now().isoformat()
        self.status = "active"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "context": self.context,
            "decision": self.decision,
            "rationale": self.rationale,
            "alternatives": self.alternatives,
            "consequences": self.consequences,
            "tags": self.tags,
            "created_at": self.created_at,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DecisionRecord":
        d = cls(
            title=data.get("title", ""),
            context=data.get("context", ""),
            decision=data.get("decision", ""),
            rationale=data.get("rationale", ""),
            alternatives=data.get("alternatives", []),
            consequences=data.get("consequences", ""),
            tags=data.get("tags", []),
        )
        d.id = data.get("id", d.id)
        d.created_at = data.get("created_at", d.created_at)
        d.status = data.get("status", "active")
        return d


class DecisionHistory:
    def __init__(self):
        self._decisions: dict[str, DecisionRecord] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if DECISIONS_FILE.exists():
            try:
                data = json.loads(DECISIONS_FILE.read_text(encoding="utf-8"))
                for item in data:
                    d = DecisionRecord.from_dict(item)
                    self._decisions[d.id] = d
            except Exception:
                pass

    def _save(self):
        with self._lock:
            data = [d.to_dict() for d in self._decisions.values()]
        DECISIONS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def record(self, title: str, context: str, decision: str,
               rationale: str, alternatives: list[str] = None,
               consequences: str = "", tags: list[str] = None) -> DecisionRecord:
        d = DecisionRecord(title, context, decision, rationale, alternatives, consequences, tags)
        with self._lock:
            self._decisions[d.id] = d
        self._save()
        return d

    def update_status(self, decision_id: str, status: str):
        with self._lock:
            d = self._decisions.get(decision_id)
            if d:
                d.status = status
        self._save()

    def search(self, query: str = "", tag: str = "", status: str = "", limit: int = 20) -> list[dict]:
        results = []
        query_lower = query.lower()

        with self._lock:
            decisions = list(self._decisions.values())

        for d in decisions:
            if status and d.status != status:
                continue
            if tag and tag not in d.tags:
                continue
            if query_lower:
                searchable = f"{d.title} {d.context} {d.decision} {d.rationale}".lower()
                if query_lower not in searchable:
                    continue
            results.append(d.to_dict())

        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return results[:limit]

    def get(self, decision_id: str) -> Optional[dict]:
        with self._lock:
            d = self._decisions.get(decision_id)
            return d.to_dict() if d else None

    def stats(self) -> dict:
        with self._lock:
            total = len(self._decisions)
            active = sum(1 for d in self._decisions.values() if d.status == "active")
            superseded = sum(1 for d in self._decisions.values() if d.status == "superseded")
        return {
            "total_decisions": total,
            "active": active,
            "superseded": superseded,
        }


decision_history = DecisionHistory()
