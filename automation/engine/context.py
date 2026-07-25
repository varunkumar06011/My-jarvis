import re
import threading
import time
import uuid
from typing import Any, Optional

from core.correlation import CorrelationContext


class AutomationContext:
    """Per-execution context carrying correlation IDs, variables, and metadata."""

    def __init__(
        self,
        automation_id: str = "",
        workflow_id: str = "",
        request_id: str = "",
        conversation_id: str = "",
        session_id: str = "",
        variables: Optional[dict] = None,
    ):
        self.automation_id = automation_id or uuid.uuid4().hex[:12]
        self.workflow_id = workflow_id
        self.request_id = request_id or CorrelationContext.get_request_id()
        self.conversation_id = conversation_id or CorrelationContext.get_conversation_id()
        self.session_id = session_id or CorrelationContext.get_session_id()
        self.variables: dict[str, Any] = variables or {}
        self._lock = threading.Lock()
        self.created_at = time.time()
        self._checkpoints: list[dict] = []

    def set_var(self, key: str, value: Any):
        with self._lock:
            self.variables[key] = value

    def get_var(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self.variables.get(key, default)

    def get_all_vars(self) -> dict[str, Any]:
        with self._lock:
            return dict(self.variables)

    def resolve(self, value: Any) -> Any:
        """Resolve template variables in a value (e.g. {{var_name}})."""
        if isinstance(value, str):
            # If the entire string is a single template var, return the raw value
            full_match = re.fullmatch(r"\{\{(\w+)\}\}", value.strip())
            if full_match:
                key = full_match.group(1)
                with self._lock:
                    if key in self.variables:
                        return self.variables[key]
            # Otherwise, do string substitution
            result = value
            for k, v in self.get_all_vars().items():
                result = result.replace(f"{{{{{k}}}}}", str(v))
            return result
        if isinstance(value, dict):
            return {k: self.resolve(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.resolve(v) for v in value]
        return value

    def checkpoint(self, step_name: str, data: Optional[dict] = None):
        with self._lock:
            self._checkpoints.append({
                "step": step_name,
                "timestamp": time.time(),
                "data": data or {},
            })

    def get_checkpoints(self) -> list[dict]:
        with self._lock:
            return list(self._checkpoints)

    def to_dict(self) -> dict:
        return {
            "automation_id": self.automation_id,
            "workflow_id": self.workflow_id,
            "request_id": self.request_id,
            "conversation_id": self.conversation_id,
            "session_id": self.session_id,
            "variables": self.get_all_vars(),
            "created_at": self.created_at,
            "checkpoints": self.get_checkpoints(),
        }
