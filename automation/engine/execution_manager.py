import threading
import time
import uuid
from typing import Any, Optional

from automation.engine.state_machine import StateMachine, AutomationState
from automation.engine.context import AutomationContext
from automation.engine.rollback import RollbackManager
from automation.engine.confirmations import ApprovalEngine, ApprovalStatus
from automation.engine.artifacts import artifact_manager
from automation.engine.history import automation_history
from automation.engine.workflow_engine import WorkflowEngine, WorkflowStep, StepType
from automation.policies.engine import PolicyEngine, RiskLevel
from core.event_bus import bus


class StepResult:
    def __init__(self, step_name: str, status: str, output: Any = None, error: str = ""):
        self.step_name = step_name
        self.status = status
        self.output = output
        self.error = error
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "step": self.step_name,
            "status": self.status,
            "output": self.output,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class ExecutionManager:
    """Manages the lifecycle of a single automation execution."""

    def __init__(
        self,
        workflow_engine: WorkflowEngine,
        policy_engine: PolicyEngine,
        approval_engine: ApprovalEngine,
    ):
        self._workflow_engine = workflow_engine
        self._policy_engine = policy_engine
        self._approval_engine = approval_engine
        self._executions: dict[str, dict] = {}
        self._lock = threading.Lock()

    def execute(
        self,
        workflow_id: str,
        variables: Optional[dict] = None,
        user: str = "system",
        request_id: str = "",
        conversation_id: str = "",
    ) -> dict:
        workflow = self._workflow_engine.get_workflow(workflow_id)
        if workflow is None:
            raise ValueError(f"Workflow '{workflow_id}' not found")

        ctx = AutomationContext(
            workflow_id=workflow_id,
            request_id=request_id,
            conversation_id=conversation_id,
            variables={**workflow.variables, **(variables or {})},
        )

        sm = StateMachine()
        rollback_mgr = RollbackManager()

        record = automation_history.create_record(
            automation_id=ctx.automation_id,
            workflow_id=workflow_id,
            name=workflow.name,
            user=user,
            request_id=request_id,
            conversation_id=conversation_id,
        )

        with self._lock:
            self._executions[ctx.automation_id] = {
                "ctx": ctx,
                "state_machine": sm,
                "rollback": rollback_mgr,
                "workflow": workflow,
                "record": record,
                "cancel_flag": threading.Event(),
                "pause_event": threading.Event(),
            }
        self._executions[ctx.automation_id]["pause_event"].set()

        sm.transition(AutomationState.QUEUED)
        bus.publish("AutomationQueued", {"automation_id": ctx.automation_id, "workflow_id": workflow_id})
        record.status = "queued"

        sm.transition(AutomationState.RUNNING)
        bus.publish("AutomationStarted", {"automation_id": ctx.automation_id, "workflow_id": workflow_id})
        record.status = "running"
        record.start_time = time.time()

        try:
            for step in workflow.steps:
                exec_data = self._executions[ctx.automation_id]

                if exec_data["cancel_flag"].is_set():
                    sm.transition(AutomationState.CANCELLED)
                    bus.publish("AutomationCancelled", {"automation_id": ctx.automation_id})
                    record.finish("cancelled")
                    return self._build_result(ctx, sm, record, rollback_mgr)

                exec_data["pause_event"].wait()
                if exec_data["cancel_flag"].is_set():
                    sm.transition(AutomationState.CANCELLED)
                    bus.publish("AutomationCancelled", {"automation_id": ctx.automation_id})
                    record.finish("cancelled")
                    return self._build_result(ctx, sm, record, rollback_mgr)

                result = self._execute_step(step, ctx, exec_data)
                record.add_step(result.to_dict())

                if result.status == "failed":
                    retried = False
                    for attempt in range(step.retries):
                        sm.transition(AutomationState.RETRYING)
                        bus.publish("AutomationRetry", {
                            "automation_id": ctx.automation_id,
                            "step": step.name,
                            "attempt": attempt + 1,
                        })
                        time.sleep(step.retry_delay)
                        sm.transition(AutomationState.RUNNING)
                        result = self._execute_step(step, ctx, exec_data)
                        record.add_step(result.to_dict())
                        if result.status == "success":
                            retried = True
                            break

                    if not retried:
                        sm.transition(AutomationState.FAILED)
                        bus.publish("AutomationFailed", {
                            "automation_id": ctx.automation_id,
                            "step": step.name,
                            "error": result.error,
                        })
                        record.finish("failed", result.error)
                        return self._build_result(ctx, sm, record, rollback_mgr)

            sm.transition(AutomationState.COMPLETED)
            record.rollback_available = rollback_mgr.has_rollback()
            record.artifacts = artifact_manager.get_for_automation(ctx.automation_id)
            bus.publish("AutomationCompleted", {"automation_id": ctx.automation_id})
            record.finish("completed")
            return self._build_result(ctx, sm, record, rollback_mgr)

        except Exception as e:
            sm.transition(AutomationState.FAILED)
            bus.publish("AutomationFailed", {
                "automation_id": ctx.automation_id,
                "error": str(e),
            })
            record.finish("failed", str(e))
            return self._build_result(ctx, sm, record, rollback_mgr)

    def _execute_step(self, step: WorkflowStep, ctx: AutomationContext, exec_data: dict) -> StepResult:
        bus.publish("AutomationStepStarted", {
            "automation_id": ctx.automation_id,
            "step": step.name,
            "type": step.step_type.value,
        })

        ctx.checkpoint(step.name)

        try:
            if step.delay > 0:
                time.sleep(step.delay)

            if step.step_type == StepType.ACTION:
                result = self._execute_action(step, ctx, exec_data)
            elif step.step_type == StepType.CONDITION:
                result = self._execute_condition(step, ctx, exec_data)
            elif step.step_type == StepType.LOOP:
                result = self._execute_loop(step, ctx, exec_data)
            elif step.step_type == StepType.PARALLEL:
                result = self._execute_parallel(step, ctx, exec_data)
            elif step.step_type == StepType.DELAY:
                time.sleep(step.delay)
                result = StepResult(step.name, "success", {"delayed": step.delay})
            elif step.step_type == StepType.APPROVAL:
                result = self._execute_approval(step, ctx, exec_data)
            elif step.step_type == StepType.SUB_WORKFLOW:
                result = self._execute_sub_workflow(step, ctx, exec_data)
            elif step.step_type == StepType.TRY_CATCH:
                result = self._execute_try_catch(step, ctx, exec_data)
            else:
                result = StepResult(step.name, "failed", error=f"Unknown step type: {step.step_type}")

            bus.publish("AutomationStepCompleted", {
                "automation_id": ctx.automation_id,
                "step": step.name,
                "status": result.status,
            })
            return result

        except Exception as e:
            bus.publish("AutomationStepCompleted", {
                "automation_id": ctx.automation_id,
                "step": step.name,
                "status": "failed",
                "error": str(e),
            })
            return StepResult(step.name, "failed", error=str(e))

    def _execute_action(self, step: WorkflowStep, ctx: AutomationContext, exec_data: dict) -> StepResult:
        handler = self._workflow_engine.get_handler(step.action)
        if handler is None:
            return StepResult(step.name, "failed", error=f"No handler for action: {step.action}")

        resolved_params = ctx.resolve(step.params)

        if self._policy_engine.needs_approval(step.action):
            sm = exec_data["state_machine"]
            sm.transition(AutomationState.WAITING_APPROVAL)
            risk = self._policy_engine.get_risk(step.action)
            req = self._approval_engine.request(
                automation_id=ctx.automation_id,
                action=step.action,
                summary=step.approval_summary or f"Execute {step.action}",
                risk_level=risk.value,
            )
            bus.publish("AutomationApprovalRequested", {
                "automation_id": ctx.automation_id,
                "approval_id": req.id,
                "action": step.action,
            })

            status = req.wait()
            if status == ApprovalStatus.APPROVED:
                sm.transition(AutomationState.RUNNING)
                bus.publish("AutomationApproved", {"automation_id": ctx.automation_id})
            elif status == ApprovalStatus.MODIFIED and req.modified_params:
                sm.transition(AutomationState.RUNNING)
                resolved_params.update(req.modified_params)
                bus.publish("AutomationApproved", {"automation_id": ctx.automation_id, "modified": True})
            else:
                bus.publish("AutomationRejected", {"automation_id": ctx.automation_id})
                return StepResult(step.name, "failed", error=f"Approval {status.value}")

        output = handler(resolved_params, ctx, exec_data["rollback"])
        return StepResult(step.name, "success", output)

    def _execute_condition(self, step: WorkflowStep, ctx: AutomationContext, exec_data: dict) -> StepResult:
        condition_met = self._evaluate_condition(step.condition, ctx)
        body = step.body if condition_met else step.else_body

        for sub_step_data in body:
            sub_step = WorkflowStep.from_dict(sub_step_data)
            result = self._execute_step(sub_step, ctx, exec_data)
            if result.status == "failed":
                return result

        return StepResult(step.name, "success", {"condition_met": condition_met})

    def _execute_loop(self, step: WorkflowStep, ctx: AutomationContext, exec_data: dict) -> StepResult:
        items = ctx.get_var(step.items, [])
        if isinstance(items, str):
            items = items.split(",")

        results = []
        for i, item in enumerate(items):
            ctx.set_var("loop_index", i)
            ctx.set_var("loop_item", item)

            for sub_step_data in step.body:
                sub_step = WorkflowStep.from_dict(sub_step_data)
                result = self._execute_step(sub_step, ctx, exec_data)
                results.append(result.to_dict())
                if result.status == "failed":
                    return StepResult(step.name, "failed", error=f"Loop iteration {i} failed")

        return StepResult(step.name, "success", {"iterations": len(items), "results": results})

    def _execute_parallel(self, step: WorkflowStep, ctx: AutomationContext, exec_data: dict) -> StepResult:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = []
        with ThreadPoolExecutor(max_workers=min(len(step.body), 4)) as pool:
            futures = {}
            for sub_step_data in step.body:
                sub_step = WorkflowStep.from_dict(sub_step_data)
                future = pool.submit(self._execute_step, sub_step, ctx, exec_data)
                futures[future] = sub_step.name

            for future in as_completed(futures):
                result = future.result()
                results.append(result.to_dict())
                if result.status == "failed":
                    return StepResult(step.name, "failed", error=f"Parallel step {futures[future]} failed")

        return StepResult(step.name, "success", {"parallel_results": results})

    def _execute_approval(self, step: WorkflowStep, ctx: AutomationContext, exec_data: dict) -> StepResult:
        sm = exec_data["state_machine"]
        sm.transition(AutomationState.WAITING_APPROVAL)

        req = self._approval_engine.request(
            automation_id=ctx.automation_id,
            action=step.action or "manual_approval",
            summary=step.approval_summary or f"Approval required for step: {step.name}",
            risk_level="high",
        )

        bus.publish("AutomationApprovalRequested", {
            "automation_id": ctx.automation_id,
            "approval_id": req.id,
        })

        status = req.wait()
        sm.transition(AutomationState.RUNNING)

        if status in (ApprovalStatus.APPROVED, ApprovalStatus.MODIFIED):
            return StepResult(step.name, "success", {"approval": status.value})
        return StepResult(step.name, "failed", error=f"Approval {status.value}")

    def _execute_sub_workflow(self, step: WorkflowStep, ctx: AutomationContext, exec_data: dict) -> StepResult:
        sub_workflow = self._workflow_engine.get_workflow(step.sub_workflow)
        if sub_workflow is None:
            return StepResult(step.name, "failed", error=f"Sub-workflow '{step.sub_workflow}' not found")

        for sub_step in sub_workflow.steps:
            result = self._execute_step(sub_step, ctx, exec_data)
            if result.status == "failed":
                return StepResult(step.name, "failed", error=f"Sub-workflow step failed: {result.error}")

        return StepResult(step.name, "success", {"sub_workflow": step.sub_workflow})

    def _execute_try_catch(self, step: WorkflowStep, ctx: AutomationContext, exec_data: dict) -> StepResult:
        try:
            for sub_step_data in step.try_body:
                sub_step = WorkflowStep.from_dict(sub_step_data)
                result = self._execute_step(sub_step, ctx, exec_data)
                if result.status == "failed":
                    raise Exception(result.error)
            return StepResult(step.name, "success")
        except Exception as e:
            for sub_step_data in step.catch_body:
                sub_step = WorkflowStep.from_dict(sub_step_data)
                self._execute_step(sub_step, ctx, exec_data)
            return StepResult(step.name, "success", {"caught_error": str(e)})

    def _evaluate_condition(self, condition: Optional[str], ctx: AutomationContext) -> bool:
        if not condition:
            return False

        condition = ctx.resolve(condition)

        try:
            return bool(eval(condition, {"__builtins__": {}}, ctx.get_all_vars()))
        except Exception:
            return False

    def _build_result(self, ctx, sm, record, rollback_mgr) -> dict:
        return {
            "automation_id": ctx.automation_id,
            "workflow_id": ctx.workflow_id,
            "state": sm.state.value,
            "status": record.status,
            "duration_ms": round(record.duration_ms, 2),
            "steps": record.steps,
            "error": record.error,
            "rollback_available": rollback_mgr.has_rollback(),
            "artifacts": artifact_manager.get_for_automation(ctx.automation_id),
            "variables": ctx.get_all_vars(),
        }

    def pause(self, automation_id: str) -> bool:
        with self._lock:
            exec_data = self._executions.get(automation_id)
        if exec_data and exec_data["state_machine"].is_running():
            exec_data["state_machine"].transition(AutomationState.PAUSED)
            exec_data["pause_event"].clear()
            bus.publish("AutomationPaused", {"automation_id": automation_id})
            return True
        return False

    def resume(self, automation_id: str) -> bool:
        with self._lock:
            exec_data = self._executions.get(automation_id)
        if exec_data and exec_data["state_machine"].state == AutomationState.PAUSED:
            exec_data["state_machine"].transition(AutomationState.RUNNING)
            exec_data["pause_event"].set()
            bus.publish("AutomationResumed", {"automation_id": automation_id})
            return True
        return False

    def cancel(self, automation_id: str) -> bool:
        with self._lock:
            exec_data = self._executions.get(automation_id)
        if exec_data and not exec_data["state_machine"].is_terminal():
            exec_data["cancel_flag"].set()
            exec_data["pause_event"].set()
            return True
        return False

    def rollback(self, automation_id: str) -> dict:
        with self._lock:
            exec_data = self._executions.get(automation_id)
        if exec_data:
            results = exec_data["rollback"].rollback_all()
            exec_data["state_machine"].transition(AutomationState.ROLLED_BACK)
            bus.publish("AutomationRollback", {"automation_id": automation_id, "results": results})
            return {"automation_id": automation_id, "rollback": results}
        return {"error": "Automation not found"}

    def get_status(self, automation_id: str) -> Optional[dict]:
        with self._lock:
            exec_data = self._executions.get(automation_id)
        if exec_data:
            return {
                "automation_id": automation_id,
                "state": exec_data["state_machine"].state.value,
                "context": exec_data["ctx"].to_dict(),
                "rollback_actions": exec_data["rollback"].get_actions(),
                "record": exec_data["record"].to_dict(),
            }
        return None

    def list_active(self) -> list[str]:
        with self._lock:
            return [
                aid for aid, ed in self._executions.items()
                if not ed["state_machine"].is_terminal()
            ]
