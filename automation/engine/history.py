import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Optional


class AutomationRecord:
    __slots__ = (
        "id", "workflow_id", "name", "status", "steps", "start_time",
        "end_time", "duration_ms", "user", "error", "rollback_available",
        "artifacts", "request_id", "conversation_id", "automation_id",
    )

    def __init__(
        self,
        automation_id: str,
        workflow_id: str,
        name: str,
        user: str = "system",
        request_id: str = "",
        conversation_id: str = "",
    ):
        self.id = uuid.uuid4().hex[:12]
        self.automation_id = automation_id
        self.workflow_id = workflow_id
        self.name = name
        self.status = "created"
        self.steps: list[dict] = []
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.duration_ms: float = 0
        self.user = user
        self.error: Optional[str] = None
        self.rollback_available = False
        self.artifacts: list[dict] = []
        self.request_id = request_id
        self.conversation_id = conversation_id

    def add_step(self, step: dict):
        self.steps.append(step)

    def finish(self, status: str, error: Optional[str] = None):
        self.status = status
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.error = error

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "automation_id": self.automation_id,
            "workflow_id": self.workflow_id,
            "name": self.name,
            "status": self.status,
            "steps": self.steps,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": round(self.duration_ms, 2),
            "user": self.user,
            "error": self.error,
            "rollback_available": self.rollback_available,
            "artifacts": self.artifacts,
            "request_id": self.request_id,
            "conversation_id": self.conversation_id,
        }


class AutomationHistory:
    def __init__(self, persist_path: Path = Path("data/automation_history.json")):
        self._persist_path = persist_path
        self._records: list[AutomationRecord] = []
        self._lock = threading.Lock()
        self._max_records = 1000

    def create_record(self, **kwargs) -> AutomationRecord:
        record = AutomationRecord(**kwargs)
        with self._lock:
            self._records.append(record)
            if len(self._records) > self._max_records:
                self._records = self._records[-self._max_records:]
        return record

    def get_record(self, record_id: str) -> Optional[AutomationRecord]:
        with self._lock:
            for r in self._records:
                if r.id == record_id:
                    return r
        return None

    def get_by_automation_id(self, automation_id: str) -> Optional[AutomationRecord]:
        with self._lock:
            for r in self._records:
                if r.automation_id == automation_id:
                    return r
        return None

    def list_records(self, limit: int = 50, status: Optional[str] = None) -> list[dict]:
        with self._lock:
            records = list(reversed(self._records))

        results = []
        for r in records:
            if status and r.status != status:
                continue
            results.append(r.to_dict())
            if len(results) >= limit:
                break
        return results

    def persist(self):
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            data = [r.to_dict() for r in self._records]
        with open(self._persist_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def summary(self) -> dict:
        with self._lock:
            total = len(self._records)
            by_status: dict[str, int] = {}
            for r in self._records:
                by_status[r.status] = by_status.get(r.status, 0) + 1

        return {
            "total": total,
            "by_status": by_status,
        }


automation_history = AutomationHistory()
