import importlib
import json
import threading
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from automation.engine.context import AutomationContext
from automation.engine.variables import VariableStore


class StepType(str, Enum):
    ACTION = "action"
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    DELAY = "delay"
    APPROVAL = "approval"
    SUB_WORKFLOW = "sub_workflow"
    TRY_CATCH = "try_catch"


class WorkflowStep:
    def __init__(
        self,
        name: str,
        step_type: StepType = StepType.ACTION,
        action: str = "",
        params: Optional[dict] = None,
        condition: Optional[str] = None,
        items: Optional[str] = None,
        body: Optional[list] = None,
        else_body: Optional[list] = None,
        delay: float = 0,
        timeout: float = 300,
        retries: int = 0,
        retry_delay: float = 5,
        approval_summary: str = "",
        sub_workflow: str = "",
        try_body: Optional[list] = None,
        catch_body: Optional[list] = None,
        on_success: Optional[list] = None,
        on_failure: Optional[list] = None,
    ):
        self.id = uuid.uuid4().hex[:8]
        self.name = name
        self.step_type = step_type
        self.action = action
        self.params = params or {}
        self.condition = condition
        self.items = items
        self.body = body or []
        self.else_body = else_body or []
        self.delay = delay
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay
        self.approval_summary = approval_summary
        self.sub_workflow = sub_workflow
        self.try_body = try_body or []
        self.catch_body = catch_body or []
        self.on_success = on_success or []
        self.on_failure = on_failure or []

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowStep":
        step_type = StepType(data.get("type", "action"))
        return cls(
            name=data.get("name", "unnamed"),
            step_type=step_type,
            action=data.get("action", ""),
            params=data.get("params", {}),
            condition=data.get("condition"),
            items=data.get("items"),
            body=data.get("body", []),
            else_body=data.get("else_body", []),
            delay=data.get("delay", 0),
            timeout=data.get("timeout", 300),
            retries=data.get("retries", 0),
            retry_delay=data.get("retry_delay", 5),
            approval_summary=data.get("approval_summary", ""),
            sub_workflow=data.get("sub_workflow", ""),
            try_body=data.get("try", []),
            catch_body=data.get("catch", []),
            on_success=data.get("on_success", []),
            on_failure=data.get("on_failure", []),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.step_type.value,
            "action": self.action,
            "params": self.params,
            "condition": self.condition,
            "items": self.items,
            "body": self.body,
            "else_body": self.else_body,
            "delay": self.delay,
            "timeout": self.timeout,
            "retries": self.retries,
            "retry_delay": self.retry_delay,
            "approval_summary": self.approval_summary,
            "sub_workflow": self.sub_workflow,
            "try_body": self.try_body,
            "catch_body": self.catch_body,
            "on_success": self.on_success,
            "on_failure": self.on_failure,
        }


class Workflow:
    def __init__(
        self,
        workflow_id: str,
        name: str,
        description: str = "",
        steps: Optional[list[WorkflowStep]] = None,
        variables: Optional[dict] = None,
        version: str = "1.0",
    ):
        self.id = workflow_id
        self.name = name
        self.description = description
        self.steps = steps or []
        self.variables = variables or {}
        self.version = version

    @classmethod
    def from_dict(cls, data: dict) -> "Workflow":
        steps = [WorkflowStep.from_dict(s) for s in data.get("steps", [])]
        return cls(
            workflow_id=data.get("id", uuid.uuid4().hex[:12]),
            name=data.get("name", "unnamed"),
            description=data.get("description", ""),
            steps=steps,
            variables=data.get("variables", {}),
            version=data.get("version", "1.0"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "variables": self.variables,
            "version": self.version,
        }


class WorkflowEngine:
    """Parses and manages workflow definitions from JSON, YAML, or Python plugins."""

    def __init__(self):
        self._workflows: dict[str, Workflow] = {}
        self._lock = threading.Lock()
        self._action_handlers: dict[str, Callable] = {}

    def register_action(self, action: str, handler: Callable):
        self._action_handlers[action] = handler

    def register_workflow(self, workflow: Workflow):
        with self._lock:
            self._workflows[workflow.id] = workflow

    def load_json(self, filepath: str | Path) -> Workflow:
        path = Path(filepath)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        workflow = Workflow.from_dict(data)
        self.register_workflow(workflow)
        return workflow

    def load_yaml(self, filepath: str | Path) -> Workflow:
        import yaml
        path = Path(filepath)
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        workflow = Workflow.from_dict(data)
        self.register_workflow(workflow)
        return workflow

    def load_python(self, filepath: str | Path) -> Workflow:
        path = Path(filepath)
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if hasattr(module, "create_workflow"):
            workflow = module.create_workflow()
            self.register_workflow(workflow)
            return workflow
        raise ValueError(f"Python workflow file {path} must define create_workflow()")

    def load_file(self, filepath: str | Path) -> Workflow:
        path = Path(filepath)
        ext = path.suffix.lower()
        if ext == ".json":
            return self.load_json(path)
        elif ext in (".yaml", ".yml"):
            return self.load_yaml(path)
        elif ext == ".py":
            return self.load_python(path)
        raise ValueError(f"Unsupported workflow file type: {ext}")

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        with self._lock:
            return self._workflows.get(workflow_id)

    def list_workflows(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "id": w.id,
                    "name": w.name,
                    "description": w.description,
                    "step_count": len(w.steps),
                    "version": w.version,
                }
                for w in self._workflows.values()
            ]

    def get_handler(self, action: str) -> Optional[Callable]:
        return self._action_handlers.get(action)

    def remove_workflow(self, workflow_id: str):
        with self._lock:
            self._workflows.pop(workflow_id, None)


workflow_engine = WorkflowEngine()
