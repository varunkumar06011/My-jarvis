import threading
import time
import uuid
from queue import PriorityQueue
from typing import Any, Callable, Optional

from core.event_bus import bus


class QueuedTask:
    def __init__(
        self,
        automation_id: str,
        workflow_id: str,
        variables: Optional[dict] = None,
        priority: int = 5,
        scheduled_time: float = 0,
        callback: Optional[Callable] = None,
    ):
        self.automation_id = automation_id
        self.workflow_id = workflow_id
        self.variables = variables or {}
        self.priority = priority
        self.scheduled_time = scheduled_time or time.time()
        self.callback = callback
        self.id = uuid.uuid4().hex[:8]

    def __lt__(self, other):
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.scheduled_time < other.scheduled_time


class QueueManager:
    """Priority queue for automation tasks."""

    def __init__(self, max_workers: int = 2):
        self._queue: PriorityQueue = PriorityQueue()
        self._max_workers = max_workers
        self._running = False
        self._threads: list[threading.Thread] = []
        self._active_count = 0
        self._lock = threading.Lock()
        self._executor_fn: Optional[Callable] = None

    def set_executor(self, fn: Callable):
        """Set the function that executes a queued task."""
        self._executor_fn = fn

    def enqueue(
        self,
        automation_id: str,
        workflow_id: str,
        variables: Optional[dict] = None,
        priority: int = 5,
        scheduled_time: float = 0,
        callback: Optional[Callable] = None,
    ) -> QueuedTask:
        task = QueuedTask(automation_id, workflow_id, variables, priority, scheduled_time, callback)
        self._queue.put(task)
        bus.publish("AutomationQueued", {
            "automation_id": automation_id,
            "workflow_id": workflow_id,
            "priority": priority,
        })
        return task

    def start(self):
        if self._running:
            return
        self._running = True
        for i in range(self._max_workers):
            t = threading.Thread(target=self._worker_loop, daemon=True, name=f"auto-worker-{i}")
            t.start()
            self._threads.append(t)
        print(f"[QueueManager] Started {self._max_workers} workers")

    def stop(self):
        self._running = False

    def _worker_loop(self):
        while self._running:
            try:
                task = self._queue.get(timeout=1)
            except Exception:
                continue

            if task is None:
                continue

            # Wait until scheduled time
            now = time.time()
            if task.scheduled_time > now:
                delay = task.scheduled_time - now
                time.sleep(min(delay, 60))
                if task.scheduled_time > time.time():
                    self._queue.put(task)
                    continue

            with self._lock:
                self._active_count += 1

            try:
                if self._executor_fn:
                    result = self._executor_fn(task)
                    if task.callback:
                        task.callback(result)
            except Exception as e:
                print(f"[QueueManager] Task {task.automation_id} failed: {e}")
            finally:
                with self._lock:
                    self._active_count -= 1
                self._queue.task_done()

    def pending_count(self) -> int:
        return self._queue.qsize()

    def active_count(self) -> int:
        with self._lock:
            return self._active_count

    def status(self) -> dict:
        return {
            "pending": self.pending_count(),
            "active": self.active_count(),
            "workers": self._max_workers,
            "running": self._running,
        }


queue_manager = QueueManager()
