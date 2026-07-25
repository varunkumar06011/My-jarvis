import json
import threading
import time
from collections import defaultdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class LogLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    AUDIT = "AUDIT"
    SECURITY = "SECURITY"
    PERFORMANCE = "PERFORMANCE"


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

STRUCTURED_LOG_FILE = LOG_DIR / "jarvis_structured.jsonl"


class StructuredLogger:
    """Enterprise structured JSON logger with severity levels."""

    def __init__(self, log_file: Path = STRUCTURED_LOG_FILE):
        self._log_file = log_file
        self._lock = threading.Lock()
        self._level_counts: dict[str, int] = defaultdict(int)

    def log(
        self,
        level: LogLevel,
        category: str,
        message: str,
        metadata: Optional[dict] = None,
        request_id: str = "",
        session_id: str = "",
        source: str = "",
    ):
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "epoch": time.time(),
            "level": level.value,
            "category": category,
            "message": message,
            "metadata": metadata or {},
            "request_id": request_id,
            "session_id": session_id,
            "source": source,
        }

        with self._lock:
            self._level_counts[level.value] += 1

            try:
                with open(self._log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception:
                pass

        # Also print to console with color
        prefix = f"[{entry['timestamp']}] [{level.value}]"
        print(f"{prefix} {category}: {message}")

        return entry

    def info(self, category: str, message: str, **kwargs):
        return self.log(LogLevel.INFO, category, message, **kwargs)

    def warning(self, category: str, message: str, **kwargs):
        return self.log(LogLevel.WARNING, category, message, **kwargs)

    def error(self, category: str, message: str, **kwargs):
        return self.log(LogLevel.ERROR, category, message, **kwargs)

    def critical(self, category: str, message: str, **kwargs):
        return self.log(LogLevel.CRITICAL, category, message, **kwargs)

    def audit(self, category: str, message: str, **kwargs):
        return self.log(LogLevel.AUDIT, category, message, **kwargs)

    def security(self, category: str, message: str, **kwargs):
        return self.log(LogLevel.SECURITY, category, message, **kwargs)

    def performance(self, category: str, message: str, **kwargs):
        return self.log(LogLevel.PERFORMANCE, category, message, **kwargs)

    def query(
        self,
        level: Optional[LogLevel] = None,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        if not self._log_file.exists():
            return []

        results = []
        try:
            with open(self._log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in reversed(lines):
                try:
                    entry = json.loads(line.strip())
                    if level and entry.get("level") != level.value:
                        continue
                    if category and entry.get("category") != category:
                        continue
                    results.append(entry)
                    if len(results) >= limit:
                        break
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass

        return results

    def summary(self) -> dict:
        with self._lock:
            return dict(self._level_counts)


structured_logger = StructuredLogger()
