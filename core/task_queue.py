import itertools
import threading
from queue import PriorityQueue
from concurrent.futures import ThreadPoolExecutor

from core.event_bus import bus

PRIORITY_HIGH = 0
PRIORITY_NORMAL = 5
PRIORITY_LOW = 10


class TaskQueue:
    def __init__(self, max_workers=2):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks = PriorityQueue()
        self._counter = itertools.count()
        self._running = False
        self._thread = None
        self._lock = threading.Lock()

    def submit(self, name, fn, *args, priority=PRIORITY_NORMAL, **kwargs):
        future = self._executor.submit(fn, *args, **kwargs)

        def _on_done(f):
            if f.exception():
                bus.publish("TaskFailed", {"name": name, "error": str(f.exception())})
                print(f"[TaskQueue] ❌ {name} failed: {f.exception()}")
            else:
                bus.publish("TaskCompleted", {"name": name, "result": f.result()})
                print(f"[TaskQueue] ✅ {name} completed")

        future.add_done_callback(_on_done)

        with self._lock:
            self._tasks.put((priority, next(self._counter), name))

        bus.publish("TaskStarted", {"name": name, "priority": priority})
        return future

    def pending_count(self):
        return self._tasks.qsize()

    def shutdown(self):
        self._executor.shutdown(wait=False)


task_queue = TaskQueue()
