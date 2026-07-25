import threading
import time
import uuid
from typing import Callable, Optional

from core.event_bus import bus


class ScheduledJob:
    def __init__(
        self,
        name: str,
        workflow_id: str,
        schedule_type: str,
        interval: float = 0,
        cron_expr: str = "",
        run_once: bool = False,
        delay: float = 0,
        variables: Optional[dict] = None,
        time_window_start: float = 0,
        time_window_end: float = 0,
        depends_on: Optional[list[str]] = None,
    ):
        self.id = uuid.uuid4().hex[:8]
        self.name = name
        self.workflow_id = workflow_id
        self.schedule_type = schedule_type  # "one_time", "recurring", "delayed"
        self.interval = interval
        self.cron_expr = cron_expr
        self.run_once = run_once
        self.delay = delay
        self.variables = variables or {}
        self.time_window_start = time_window_start
        self.time_window_end = time_window_end
        self.depends_on = depends_on or []
        self.next_run = time.time() + delay if delay > 0 else time.time()
        self.last_run: Optional[float] = None
        self.run_count = 0
        self.enabled = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "workflow_id": self.workflow_id,
            "schedule_type": self.schedule_type,
            "interval": self.interval,
            "run_once": self.run_once,
            "delay": self.delay,
            "next_run": self.next_run,
            "last_run": self.last_run,
            "run_count": self.run_count,
            "enabled": self.enabled,
        }


class Scheduler:
    """Scheduler for one-time, recurring, and delayed automation jobs."""

    def __init__(self):
        self._jobs: dict[str, ScheduledJob] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._on_trigger: Optional[Callable] = None

    def set_trigger_callback(self, fn: Callable):
        """Set the callback called when a job is triggered. fn(job) -> result."""
        self._on_trigger = fn

    def schedule_one_time(self, name: str, workflow_id: str, delay: float = 0, **kwargs) -> ScheduledJob:
        job = ScheduledJob(
            name=name,
            workflow_id=workflow_id,
            schedule_type="one_time",
            delay=delay,
            run_once=True,
            variables=kwargs.get("variables"),
        )
        with self._lock:
            self._jobs[job.id] = job
        return job

    def schedule_recurring(self, name: str, workflow_id: str, interval: float, **kwargs) -> ScheduledJob:
        job = ScheduledJob(
            name=name,
            workflow_id=workflow_id,
            schedule_type="recurring",
            interval=interval,
            variables=kwargs.get("variables"),
        )
        with self._lock:
            self._jobs[job.id] = job
        return job

    def schedule_delayed(self, name: str, workflow_id: str, delay: float, **kwargs) -> ScheduledJob:
        job = ScheduledJob(
            name=name,
            workflow_id=workflow_id,
            schedule_type="delayed",
            delay=delay,
            run_once=True,
            variables=kwargs.get("variables"),
        )
        with self._lock:
            self._jobs[job.id] = job
        return job

    def cancel_job(self, job_id: str) -> bool:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].enabled = False
                del self._jobs[job_id]
                return True
        return False

    def enable_job(self, job_id: str):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].enabled = True

    def disable_job(self, job_id: str):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].enabled = False

    def list_jobs(self) -> list[dict]:
        with self._lock:
            return [j.to_dict() for j in self._jobs.values()]

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="scheduler")
        self._thread.start()
        print("[Scheduler] Started")

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            now = time.time()
            to_run = []

            with self._lock:
                for job in self._jobs.values():
                    if not job.enabled:
                        continue
                    if job.next_run <= now:
                        to_run.append(job)

            for job in to_run:
                try:
                    bus.publish("AutomationScheduled", {
                        "job_id": job.id,
                        "workflow_id": job.workflow_id,
                    })
                    if self._on_trigger:
                        self._on_trigger(job)
                    job.last_run = now
                    job.run_count += 1

                    if job.run_once:
                        with self._lock:
                            self._jobs.pop(job.id, None)
                    else:
                        job.next_run = now + job.interval
                except Exception as e:
                    print(f"[Scheduler] Job {job.name} failed: {e}")

            time.sleep(1)


scheduler = Scheduler()
