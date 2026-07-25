import json
import threading
import time
import traceback
from collections import defaultdict, deque
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class TelemetryLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    PERFORMANCE = "performance"


TELEMETRY_DIR = Path("data/telemetry")
TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)

TELEMETRY_FILE = TELEMETRY_DIR / "telemetry.jsonl"
CRASH_FILE = TELEMETRY_DIR / "crashes.jsonl"
PERFORMANCE_FILE = TELEMETRY_DIR / "performance.jsonl"


class TelemetryCollector:
    """Local-only telemetry. Never uploads anything."""

    def __init__(self, max_entries: int = 5000):
        self._entries: deque = deque(maxlen=max_entries)
        self._lock = threading.Lock()
        self._error_counts: dict[str, int] = defaultdict(int)
        self._warning_counts: dict[str, int] = defaultdict(int)

    def record(
        self,
        level: TelemetryLevel,
        category: str,
        message: str,
        metadata: Optional[dict] = None,
        request_id: str = "",
    ):
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "epoch": time.time(),
            "level": level.value,
            "category": category,
            "message": message,
            "metadata": metadata or {},
            "request_id": request_id,
        }

        with self._lock:
            self._entries.append(entry)

            if level == TelemetryLevel.ERROR:
                self._error_counts[category] += 1
            elif level == TelemetryLevel.WARNING:
                self._warning_counts[category] += 1

        self._persist(entry, level)
        return entry

    def record_crash(self, category: str, exc: Exception, metadata: Optional[dict] = None):
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "epoch": time.time(),
            "level": "crash",
            "category": category,
            "exception_type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
            "metadata": metadata or {},
        }

        with self._lock:
            self._entries.append(entry)
            self._error_counts[category] += 1

        self._persist_crash(entry)
        return entry

    def record_performance(self, operation: str, duration_ms: float, metadata: Optional[dict] = None):
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "epoch": time.time(),
            "level": "performance",
            "operation": operation,
            "duration_ms": round(duration_ms, 2),
            "metadata": metadata or {},
        }

        with self._lock:
            self._entries.append(entry)

        self._persist_performance(entry)
        return entry

    def _persist(self, entry: dict, level: TelemetryLevel):
        try:
            with open(TELEMETRY_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _persist_crash(self, entry: dict):
        try:
            with open(CRASH_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _persist_performance(self, entry: dict):
        try:
            with open(PERFORMANCE_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def query(
        self,
        level: Optional[TelemetryLevel] = None,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        with self._lock:
            entries = list(self._entries)

        results = []
        for e in reversed(entries):
            if level and e.get("level") != level.value:
                continue
            if category and e.get("category") != category:
                continue
            results.append(e)
            if len(results) >= limit:
                break

        return results

    def summary(self) -> dict:
        with self._lock:
            total = len(self._entries)
            errors = dict(self._error_counts)
            warnings = dict(self._warning_counts)

        return {
            "total_entries": total,
            "error_counts": errors,
            "warning_counts": warnings,
            "total_errors": sum(errors.values()),
            "total_warnings": sum(warnings.values()),
        }

    def clear(self):
        with self._lock:
            self._entries.clear()
            self._error_counts.clear()
            self._warning_counts.clear()


telemetry = TelemetryCollector()
