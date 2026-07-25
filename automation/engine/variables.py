import threading
from typing import Any, Optional


class VariableStore:
    """Thread-safe variable store for workflow execution."""

    def __init__(self):
        self._vars: dict[str, Any] = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: Any):
        with self._lock:
            self._vars[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._vars.get(key, default)

    def has(self, key: str) -> bool:
        with self._lock:
            return key in self._vars

    def delete(self, key: str):
        with self._lock:
            self._vars.pop(key, None)

    def all(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._vars)

    def clear(self):
        with self._lock:
            self._vars.clear()

    def merge(self, other: dict[str, Any]):
        with self._lock:
            self._vars.update(other)

    def resolve(self, value: Any) -> Any:
        """Resolve {{var}} references in a value."""
        if isinstance(value, str):
            result = value
            for k, v in self.all().items():
                result = result.replace(f"{{{{{k}}}}}", str(v))
            return result
        if isinstance(value, dict):
            return {k: self.resolve(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.resolve(v) for v in value]
        return value
