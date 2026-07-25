import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor

from core.event_bus import bus


class TaskQueue:
    def __init__(self, max_workers=2):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks = Queue()
        self._running = False
        self._thread = None

    def submit(self, name, fn, *args, **kwargs):
        future = self._executor.submit(fn, *args, **kwargs)

        def _on_done(f):
            if f.exception():
                bus.publish("TaskFailed", {"name": name, "error": str(f.exception())})
                print(f"[TaskQueue] ❌ {name} failed: {f.exception()}")
            else:
                bus.publish("TaskCompleted", {"name": name, "result": f.result()})
                print(f"[TaskQueue] ✅ {name} completed")

        future.add_done_callback(_on_done)
        bus.publish("TaskStarted", {"name": name})
        return future

    def shutdown(self):
        self._executor.shutdown(wait=False)


task_queue = TaskQueue()
