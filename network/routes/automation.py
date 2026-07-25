from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional

from network.api.authentication import authenticate

router = APIRouter(prefix="/api/v1/automation", tags=["automation"])


class StartAutomationRequest(BaseModel):
    workflow_id: str
    variables: Optional[dict] = None
    priority: int = 5
    sync: bool = False


class CreateWorkflowRequest(BaseModel):
    workflow: dict


class ScheduleRequest(BaseModel):
    name: str
    workflow_id: str
    schedule_type: str = "one_time"
    interval: float = 0
    delay: float = 0
    variables: Optional[dict] = None


def _get_engine():
    from automation.engine.automation_engine import automation_engine
    return automation_engine


@router.post("/start")
async def start_automation(req: StartAutomationRequest, auth: dict = Depends(authenticate)):
    engine = _get_engine()
    if req.sync:
        result = engine.start_automation_sync(
            workflow_id=req.workflow_id,
            variables=req.variables,
        )
        return result
    return engine.start_automation(
        workflow_id=req.workflow_id,
        variables=req.variables,
        priority=req.priority,
    )


@router.post("/{automation_id}/pause")
async def pause_automation(automation_id: str, auth: dict = Depends(authenticate)):
    engine = _get_engine()
    success = engine.pause(automation_id)
    return {"status": "paused" if success else "error", "automation_id": automation_id}


@router.post("/{automation_id}/resume")
async def resume_automation(automation_id: str, auth: dict = Depends(authenticate)):
    engine = _get_engine()
    success = engine.resume(automation_id)
    return {"status": "resumed" if success else "error", "automation_id": automation_id}


@router.post("/{automation_id}/cancel")
async def cancel_automation(automation_id: str, auth: dict = Depends(authenticate)):
    engine = _get_engine()
    success = engine.cancel(automation_id)
    return {"status": "cancelled" if success else "error", "automation_id": automation_id}


@router.post("/{automation_id}/rollback")
async def rollback_automation(automation_id: str, auth: dict = Depends(authenticate)):
    engine = _get_engine()
    return engine.rollback(automation_id)


@router.get("/{automation_id}/status")
async def get_status(automation_id: str, auth: dict = Depends(authenticate)):
    engine = _get_engine()
    status = engine.get_status(automation_id)
    if status is None:
        return {"error": "Automation not found", "automation_id": automation_id}
    return status


@router.get("/history")
async def get_history(
    auth: dict = Depends(authenticate),
    limit: int = Query(default=50, le=500),
    status: Optional[str] = None,
):
    engine = _get_engine()
    return engine.get_history(limit=limit, status=status)


@router.get("/history/summary")
async def get_history_summary(auth: dict = Depends(authenticate)):
    engine = _get_engine()
    return engine.get_history_summary()


@router.get("/workflows")
async def list_workflows(auth: dict = Depends(authenticate)):
    engine = _get_engine()
    return engine.list_workflows()


@router.post("/workflows")
async def create_workflow(req: CreateWorkflowRequest, auth: dict = Depends(authenticate)):
    from automation.engine.workflow_engine import Workflow
    from automation.validators.workflow_validator import workflow_validator

    result = workflow_validator.validate_dict(req.workflow)
    if not result.valid:
        return {"status": "invalid", "errors": result.errors, "warnings": result.warnings}

    workflow = Workflow.from_dict(req.workflow)
    engine = _get_engine()
    engine.register_workflow(workflow)
    return {"status": "registered", "workflow_id": workflow.id, "name": workflow.name, "steps": len(workflow.steps)}


@router.get("/templates")
async def list_templates(auth: dict = Depends(authenticate)):
    from automation.templates.manager import template_manager
    return template_manager.list_templates()


@router.get("/templates/{template_id}")
async def get_template(template_id: str, auth: dict = Depends(authenticate)):
    from automation.templates.manager import template_manager
    template = template_manager.get_template(template_id)
    if template is None:
        return {"error": "Template not found"}
    return template


@router.post("/templates/{template_id}/start")
async def start_from_template(
    template_id: str,
    variables: Optional[dict] = None,
    auth: dict = Depends(authenticate),
):
    from automation.templates.manager import template_manager
    engine = _get_engine()
    workflow = template_manager.to_workflow(template_id, variables)
    if workflow is None:
        return {"error": "Template not found"}
    engine.register_workflow(workflow)
    return engine.start_automation(workflow_id=workflow.id, variables=variables)


@router.post("/validate")
async def validate_workflow(req: CreateWorkflowRequest, auth: dict = Depends(authenticate)):
    from automation.validators.workflow_validator import workflow_validator
    result = workflow_validator.validate_dict(req.workflow)
    return result.to_dict()


@router.get("/queue")
async def get_queue_status(auth: dict = Depends(authenticate)):
    engine = _get_engine()
    return engine.get_queue_status()


@router.get("/active")
async def list_active(auth: dict = Depends(authenticate)):
    engine = _get_engine()
    return {"active": engine.list_active()}


@router.get("/approvals")
async def get_pending_approvals(auth: dict = Depends(authenticate)):
    engine = _get_engine()
    return engine.get_pending_approvals()


@router.post("/approvals/{approval_id}/approve")
async def approve_request(approval_id: str, auth: dict = Depends(authenticate)):
    engine = _get_engine()
    success = engine.approve(approval_id)
    return {"status": "approved" if success else "error", "approval_id": approval_id}


@router.post("/approvals/{approval_id}/reject")
async def reject_request(approval_id: str, auth: dict = Depends(authenticate)):
    engine = _get_engine()
    success = engine.reject(approval_id)
    return {"status": "rejected" if success else "error", "approval_id": approval_id}


@router.get("/policies")
async def get_policies(auth: dict = Depends(authenticate)):
    engine = _get_engine()
    return engine.get_policies()


@router.get("/artifacts")
async def get_artifacts(
    auth: dict = Depends(authenticate),
    automation_id: Optional[str] = None,
    limit: int = Query(default=100, le=500),
):
    engine = _get_engine()
    return engine.get_artifacts(automation_id=automation_id, limit=limit)


# ── Scheduling ──

@router.post("/schedule")
async def create_schedule(req: ScheduleRequest, auth: dict = Depends(authenticate)):
    engine = _get_engine()
    if req.schedule_type == "one_time":
        return engine.schedule_one_time(req.name, req.workflow_id, req.delay, variables=req.variables)
    elif req.schedule_type == "recurring":
        return engine.schedule_recurring(req.name, req.workflow_id, req.interval, variables=req.variables)
    return {"error": f"Unknown schedule type: {req.schedule_type}"}


@router.get("/schedules")
async def list_schedules(auth: dict = Depends(authenticate)):
    engine = _get_engine()
    return engine.list_schedules()


@router.delete("/schedules/{job_id}")
async def cancel_schedule(job_id: str, auth: dict = Depends(authenticate)):
    engine = _get_engine()
    success = engine.cancel_schedule(job_id)
    return {"status": "cancelled" if success else "error", "job_id": job_id}


# ── Macros ──

@router.get("/macros")
async def list_macros(auth: dict = Depends(authenticate)):
    from automation.recorder.controller import macro_recorder
    return macro_recorder.list_macros()


@router.post("/macros/{macro_id}/replay")
async def replay_macro(
    macro_id: str,
    speed: str = "normal",
    auth: dict = Depends(authenticate),
):
    from automation.recorder.controller import macro_recorder
    from automation.engine.context import AutomationContext
    from automation.engine.rollback import RollbackManager
    ctx = AutomationContext()
    rollback = RollbackManager()
    return macro_recorder.replay({"macro_id": macro_id, "speed": speed}, ctx, rollback)


@router.delete("/macros/{macro_id}")
async def delete_macro(macro_id: str, auth: dict = Depends(authenticate)):
    from automation.recorder.controller import macro_recorder
    success = macro_recorder.delete_macro(macro_id)
    return {"status": "deleted" if success else "error", "macro_id": macro_id}
