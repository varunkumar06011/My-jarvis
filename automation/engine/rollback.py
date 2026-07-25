import threading
import time
import uuid
from typing import Any, Callable, Optional


class RollbackAction:
    def __init__(
        self,
        name: str,
        undo_fn: Callable,
        description: str = "",
        metadata: Optional[dict] = None,
    ):
        self.id = uuid.uuid4().hex[:12]
        self.name = name
        self.undo_fn = undo_fn
        self.description = description
        self.metadata = metadata or {}
        self.executed = False
        self.undone = False

    def undo(self) -> Any:
        if self.undone:
            return None
        result = self.undo_fn()
        self.undone = True
        return result

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "executed": self.executed,
            "undone": self.undone,
            "metadata": self.metadata,
        }


class RollbackManager:
    def __init__(self):
        self._actions: list[RollbackAction] = []
        self._lock = threading.Lock()

    def register(
        self,
        name: str,
        undo_fn: Callable,
        description: str = "",
        metadata: Optional[dict] = None,
    ) -> RollbackAction:
        action = RollbackAction(name, undo_fn, description, metadata)
        with self._lock:
            self._actions.append(action)
        return action

    def rollback_all(self) -> list[dict]:
        results = []
        with self._lock:
            actions = list(reversed(self._actions))

        for action in actions:
            if not action.undone:
                try:
                    action.undo()
                    results.append({"id": action.id, "name": action.name, "status": "undone"})
                except Exception as e:
                    results.append({"id": action.id, "name": action.name, "status": "failed", "error": str(e)})
        return results

    def rollback_one(self, action_id: str) -> dict:
        with self._lock:
            for action in self._actions:
                if action.id == action_id:
                    try:
                        action.undo()
                        return {"id": action_id, "status": "undone"}
                    except Exception as e:
                        return {"id": action_id, "status": "failed", "error": str(e)}
        return {"id": action_id, "status": "not_found"}

    def has_rollback(self) -> bool:
        with self._lock:
            return any(not a.undone for a in self._actions)

    def get_actions(self) -> list[dict]:
        with self._lock:
            return [a.to_dict() for a in self._actions]

    def clear(self):
        with self._lock:
            self._actions.clear()
