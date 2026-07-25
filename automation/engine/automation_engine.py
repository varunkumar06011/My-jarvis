import threading
import time
import uuid
from typing import Any, Callable, Optional

from automation.engine.execution_manager import ExecutionManager
from automation.engine.workflow_engine import WorkflowEngine, workflow_engine
from automation.engine.queue_manager import QueueManager, queue_manager
from automation.engine.scheduler import Scheduler, scheduler
from automation.engine.confirmations import ApprovalEngine, approval_engine
from automation.engine.artifacts import artifact_manager
from automation.engine.history import automation_history
from automation.policies.engine import PolicyEngine, policy_engine
from core.event_bus import bus
from core.correlation import CorrelationContext


class AutomationEngine:
    """Main entry point for the Enterprise Automation Platform.

    Coordinates workflow engine, execution manager, queue, scheduler,
    approvals, policies, rollback, artifacts, and history.
    """

    def __init__(self):
        self.workflow_engine = workflow_engine
        self.policy_engine = policy_engine
        self.approval_engine = approval_engine
        self.queue_manager = queue_manager
        self.scheduler = scheduler
        self.execution_manager = ExecutionManager(
            workflow_engine=self.workflow_engine,
            policy_engine=self.policy_engine,
            approval_engine=self.approval_engine,
        )
        self._running = False
        self._lock = threading.Lock()

    def start(self):
        if self._running:
            return
        self._running = True

        # Wire queue executor
        self.queue_manager.set_executor(self._execute_queued_task)
        self.queue_manager.start()

        # Wire scheduler trigger
        self.scheduler.set_trigger_callback(self._execute_scheduled_job)
        self.scheduler.start()

        bus.publish("AutomationPlatformStarted", {})
        print("[Automation] Engine started")

    def stop(self):
        self._running = False
        self.queue_manager.stop()
        self.scheduler.stop()
        automation_history.persist()
        bus.publish("AutomationPlatformStopped", {})
        print("[Automation] Engine stopped")

    def register_action(self, action: str, handler: Callable):
        """Register a handler for an automation action."""
        self.workflow_engine.register_action(action, handler)

    def register_workflow(self, workflow):
        """Register a workflow definition."""
        self.workflow_engine.register_workflow(workflow)

    def load_workflow_file(self, filepath: str) -> dict:
        """Load a workflow from a JSON, YAML, or Python file."""
        workflow = self.workflow_engine.load_file(filepath)
        return {"id": workflow.id, "name": workflow.name, "steps": len(workflow.steps)}

    def start_automation(
        self,
        workflow_id: str,
        variables: Optional[dict] = None,
        user: str = "system",
        priority: int = 5,
        request_id: str = "",
        conversation_id: str = "",
    ) -> dict:
        """Start an automation workflow execution."""
        automation_id = uuid.uuid4().hex[:12]

        bus.publish("AutomationCreated", {
            "automation_id": automation_id,
            "workflow_id": workflow_id,
            "user": user,
        })

        # Enqueue for execution
        self.queue_manager.enqueue(
            automation_id=automation_id,
            workflow_id=workflow_id,
            variables=variables,
            priority=priority,
            callback=lambda result: self._on_completion(automation_id, result),
        )

        return {
            "automation_id": automation_id,
            "workflow_id": workflow_id,
            "status": "queued",
            "queue_position": self.queue_manager.pending_count(),
        }

    def start_automation_sync(
        self,
        workflow_id: str,
        variables: Optional[dict] = None,
        user: str = "system",
        request_id: str = "",
        conversation_id: str = "",
    ) -> dict:
        """Start an automation and wait for completion (blocking)."""
        automation_id = uuid.uuid4().hex[:12]

        bus.publish("AutomationCreated", {
            "automation_id": automation_id,
            "workflow_id": workflow_id,
            "user": user,
        })

        with CorrelationContext.automation(automation_id):
            result = self.execution_manager.execute(
                workflow_id=workflow_id,
                variables=variables,
                user=user,
                request_id=request_id,
                conversation_id=conversation_id,
            )
        return result

    def _execute_queued_task(self, task) -> dict:
        """Execute a task from the queue."""
        with CorrelationContext.automation(task.automation_id):
            return self.execution_manager.execute(
                workflow_id=task.workflow_id,
                variables=task.variables,
            )

    def _execute_scheduled_job(self, job) -> dict:
        """Execute a scheduled job."""
        return self.start_automation(
            workflow_id=job.workflow_id,
            variables=job.variables,
            user="scheduler",
        )

    def _on_completion(self, automation_id: str, result: dict):
        """Callback when a queued automation completes."""
        status = result.get("status", "unknown")
        if status == "completed":
            bus.publish("AutomationCompleted", {"automation_id": automation_id})
        elif status == "failed":
            bus.publish("AutomationFailed", {"automation_id": automation_id, "error": result.get("error")})

    # ── Control operations ──

    def pause(self, automation_id: str) -> bool:
        return self.execution_manager.pause(automation_id)

    def resume(self, automation_id: str) -> bool:
        return self.execution_manager.resume(automation_id)

    def cancel(self, automation_id: str) -> bool:
        return self.execution_manager.cancel(automation_id)

    def rollback(self, automation_id: str) -> dict:
        return self.execution_manager.rollback(automation_id)

    def get_status(self, automation_id: str) -> Optional[dict]:
        return self.execution_manager.get_status(automation_id)

    # ── Query operations ──

    def list_workflows(self) -> list[dict]:
        return self.workflow_engine.list_workflows()

    def list_active(self) -> list[str]:
        return self.execution_manager.list_active()

    def get_history(self, limit: int = 50, status: Optional[str] = None) -> list[dict]:
        return automation_history.list_records(limit=limit, status=status)

    def get_history_summary(self) -> dict:
        return automation_history.summary()

    def get_queue_status(self) -> dict:
        return self.queue_manager.status()

    def get_pending_approvals(self) -> list[dict]:
        return self.approval_engine.get_pending()

    def approve(self, approval_id: str) -> bool:
        return self.approval_engine.approve(approval_id)

    def reject(self, approval_id: str) -> bool:
        return self.approval_engine.reject(approval_id)

    def get_policies(self) -> list[dict]:
        return self.policy_engine.list_policies()

    def get_artifacts(self, automation_id: Optional[str] = None, limit: int = 100) -> list[dict]:
        if automation_id:
            return artifact_manager.get_for_automation(automation_id)
        return artifact_manager.get_all(limit=limit)

    # ── Scheduling ──

    def schedule_one_time(self, name: str, workflow_id: str, delay: float = 0, **kwargs) -> dict:
        job = self.scheduler.schedule_one_time(name, workflow_id, delay, **kwargs)
        return job.to_dict()

    def schedule_recurring(self, name: str, workflow_id: str, interval: float, **kwargs) -> dict:
        job = self.scheduler.schedule_recurring(name, workflow_id, interval, **kwargs)
        return job.to_dict()

    def cancel_schedule(self, job_id: str) -> bool:
        return self.scheduler.cancel_job(job_id)

    def list_schedules(self) -> list[dict]:
        return self.scheduler.list_jobs()

    # ── Approval callback ──

    def set_approval_callback(self, callback: Callable):
        """Set a callback for approval requests (e.g. GUI dialog)."""
        self.approval_engine.set_callback(callback)


automation_engine = AutomationEngine()
