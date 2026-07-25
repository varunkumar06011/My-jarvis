import json
import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class EventCategory(str, Enum):
    WAKE_WORD = "wake_word"
    SPEECH = "speech"
    LLM = "llm"
    TOOL = "tool"
    PLUGIN = "plugin"
    API = "api"
    GUI = "gui"
    HEALTH = "health"
    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    AUTOMATION = "automation"
    SECURITY = "security"
    SYSTEM = "system"


class EventStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    WARNING = "warning"


CATEGORY_MAP = {
    "WakeWordDetected": EventCategory.WAKE_WORD,
    "SpeechStarted": EventCategory.SPEECH,
    "SpeechFinished": EventCategory.SPEECH,
    "LLMResponse": EventCategory.LLM,
    "ToolExecuted": EventCategory.TOOL,
    "PluginLoaded": EventCategory.PLUGIN,
    "TaskStarted": EventCategory.SYSTEM,
    "TaskCompleted": EventCategory.SYSTEM,
    "TaskFailed": EventCategory.SYSTEM,
    "HealthCheckPassed": EventCategory.HEALTH,
    "HealthCheckFailed": EventCategory.HEALTH,
    "HealthChanged": EventCategory.HEALTH,
    "ApplicationStarted": EventCategory.STARTUP,
    "ApplicationStopped": EventCategory.SHUTDOWN,
    "LifecycleChanged": EventCategory.SYSTEM,
    "NotificationCreated": EventCategory.GUI,
    "RecoverySucceeded": EventCategory.SYSTEM,
    "RecoveryFailed": EventCategory.SYSTEM,
    "RecoveryEscalated": EventCategory.SYSTEM,
    "RecoveryNotified": EventCategory.SYSTEM,
    "AutomationCreated": EventCategory.AUTOMATION,
    "AutomationQueued": EventCategory.AUTOMATION,
    "AutomationStarted": EventCategory.AUTOMATION,
    "AutomationPaused": EventCategory.AUTOMATION,
    "AutomationResumed": EventCategory.AUTOMATION,
    "AutomationApprovalRequested": EventCategory.AUTOMATION,
    "AutomationApproved": EventCategory.AUTOMATION,
    "AutomationRejected": EventCategory.AUTOMATION,
    "AutomationStepStarted": EventCategory.AUTOMATION,
    "AutomationStepCompleted": EventCategory.AUTOMATION,
    "AutomationRetry": EventCategory.AUTOMATION,
    "AutomationRollback": EventCategory.AUTOMATION,
    "AutomationCompleted": EventCategory.AUTOMATION,
    "AutomationFailed": EventCategory.AUTOMATION,
    "AutomationCancelled": EventCategory.AUTOMATION,
    "AutomationScheduled": EventCategory.AUTOMATION,
}


class StoredEvent:
    __slots__ = (
        "id", "timestamp", "category", "event", "source",
        "request_id", "session_id", "conversation_id", "automation_id",
        "duration_ms", "status", "metadata",
    )

    def __init__(
        self,
        event: str,
        category: EventCategory = EventCategory.SYSTEM,
        source: str = "",
        request_id: str = "",
        session_id: str = "",
        conversation_id: str = "",
        automation_id: str = "",
        duration_ms: float = 0,
        status: EventStatus = EventStatus.SUCCESS,
        metadata: Any = None,
    ):
        self.id = uuid.uuid4().hex[:12]
        self.timestamp = time.time()
        self.category = category
        self.event = event
        self.source = source
        self.request_id = request_id
        self.session_id = session_id
        self.conversation_id = conversation_id
        self.automation_id = automation_id
        self.duration_ms = duration_ms
        self.status = status
        self.metadata = metadata

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "epoch": self.timestamp,
            "category": self.category.value,
            "event": self.event,
            "source": self.source,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "automation_id": self.automation_id,
            "duration_ms": round(self.duration_ms, 2),
            "status": self.status.value,
            "metadata": self.metadata,
        }


class EventStore:
    def __init__(self, max_events: int = 10000, persist_path: Optional[Path] = None):
        self._events: deque = deque(maxlen=max_events)
        self._lock = threading.Lock()
        self._max_events = max_events
        self._persist_path = persist_path or Path("data/event_store.json")
        self._counters: dict[str, int] = defaultdict(int)

    def record(self, event: str, **kwargs) -> StoredEvent:
        category = kwargs.get("category")
        if category is None:
            cat = CATEGORY_MAP.get(event, EventCategory.SYSTEM)
            kwargs["category"] = cat

        stored = StoredEvent(event=event, **kwargs)

        with self._lock:
            self._events.append(stored)
            self._counters[event] += 1

        return stored

    def record_from_bus(self, event_type: str, data: Any = None):
        category = CATEGORY_MAP.get(event_type, EventCategory.SYSTEM)
        metadata = data if isinstance(data, dict) else {"raw": data}

        duration_ms = metadata.pop("_duration_ms", 0)
        status = EventStatus.SUCCESS
        if "error" in metadata or "failed" in str(metadata).lower():
            status = EventStatus.FAILED

        request_id = metadata.pop("request_id", "")
        session_id = metadata.pop("session_id", "")
        conversation_id = metadata.pop("conversation_id", "")
        automation_id = metadata.pop("automation_id", "")

        return self.record(
            event_type,
            category=category,
            duration_ms=duration_ms,
            status=status,
            metadata=metadata,
            request_id=request_id,
            session_id=session_id,
            conversation_id=conversation_id,
            automation_id=automation_id,
        )

    def search(
        self,
        category: Optional[EventCategory] = None,
        event: Optional[str] = None,
        source: Optional[str] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        status: Optional[EventStatus] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100,
    ) -> list[dict]:
        results = []

        with self._lock:
            events = list(self._events)

        for e in reversed(events):
            if category and e.category != category:
                continue
            if event and e.event != event:
                continue
            if source and e.source != source:
                continue
            if request_id and e.request_id != request_id:
                continue
            if session_id and e.session_id != session_id:
                continue
            if status and e.status != status:
                continue
            if start_time and e.timestamp < start_time:
                continue
            if end_time and e.timestamp > end_time:
                continue

            results.append(e.to_dict())
            if len(results) >= limit:
                break

        return results

    def timeline(self, limit: int = 50, since: Optional[float] = None) -> list[dict]:
        with self._lock:
            events = list(self._events)

        results = []
        for e in reversed(events):
            if since and e.timestamp < since:
                continue
            results.append(e.to_dict())
            if len(results) >= limit:
                break

        return results

    def statistics(self) -> dict:
        with self._lock:
            total = len(self._events)
            counters = dict(self._counters)
            events = list(self._events)

        by_category: dict[str, int] = defaultdict(int)
        by_status: dict[str, int] = defaultdict(int)

        for e in events:
            by_category[e.category.value] += 1
            by_status[e.status.value] += 1

        avg_duration: dict[str, float] = {}
        cat_durations: dict[str, list[float]] = defaultdict(list)
        for e in events:
            if e.duration_ms > 0:
                cat_durations[e.category.value].append(e.duration_ms)

        for cat, durations in cat_durations.items():
            avg_duration[cat] = round(sum(durations) / len(durations), 2)

        return {
            "total_events": total,
            "by_event": counters,
            "by_category": dict(by_category),
            "by_status": dict(by_status),
            "avg_duration_ms": avg_duration,
        }

    def export(self, filepath: Optional[Path] = None) -> Path:
        path = filepath or self._persist_path
        path.parent.mkdir(parents=True, exist_ok=True)

        with self._lock:
            events = [e.to_dict() for e in self._events]

        with open(path, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2, ensure_ascii=False)

        return path

    def get_event(self, event_id: str) -> Optional[dict]:
        with self._lock:
            for e in self._events:
                if e.id == event_id:
                    return e.to_dict()
        return None

    def replay(self, start_time: Optional[float] = None, end_time: Optional[float] = None) -> list[dict]:
        with self._lock:
            events = list(self._events)

        results = []
        for e in events:
            if start_time and e.timestamp < start_time:
                continue
            if end_time and e.timestamp > end_time:
                continue
            results.append(e.to_dict())

        return results

    def clear(self):
        with self._lock:
            self._events.clear()
            self._counters.clear()

    def count(self) -> int:
        with self._lock:
            return len(self._events)


event_store = EventStore()


def subscribe_event_store_to_bus():
    """Subscribe EventStore to all events on the EventBus."""
    from core.event_bus import bus

    known_events = list(CATEGORY_MAP.keys())

    for event_type in known_events:
        bus.subscribe(event_type, lambda data, et=event_type: event_store.record_from_bus(et, data))

    # Catch-all for unknown events
    def catch_all(event_type, data):
        if event_type not in known_events:
            event_store.record_from_bus(event_type, data)

    # Subscribe to a broad set of additional events
    for et in ["PluginLoaded", "NotificationCreated", "LifecycleChanged", "HealthChanged"]:
        if et not in known_events:
            bus.subscribe(et, lambda data, et=et: event_store.record_from_bus(et, data))
