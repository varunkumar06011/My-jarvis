from enum import Enum
from typing import Optional


class AutomationState(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


VALID_TRANSITIONS: dict[AutomationState, list[AutomationState]] = {
    AutomationState.CREATED: [AutomationState.QUEUED, AutomationState.CANCELLED],
    AutomationState.QUEUED: [AutomationState.RUNNING, AutomationState.CANCELLED],
    AutomationState.RUNNING: [
        AutomationState.PAUSED,
        AutomationState.WAITING_APPROVAL,
        AutomationState.RETRYING,
        AutomationState.COMPLETED,
        AutomationState.FAILED,
        AutomationState.CANCELLED,
        AutomationState.ROLLED_BACK,
    ],
    AutomationState.PAUSED: [AutomationState.RUNNING, AutomationState.CANCELLED],
    AutomationState.WAITING_APPROVAL: [
        AutomationState.RUNNING,
        AutomationState.FAILED,
        AutomationState.CANCELLED,
    ],
    AutomationState.RETRYING: [
        AutomationState.RUNNING,
        AutomationState.FAILED,
        AutomationState.CANCELLED,
    ],
    AutomationState.COMPLETED: [AutomationState.ROLLED_BACK],
    AutomationState.FAILED: [AutomationState.ROLLED_BACK, AutomationState.RETRYING],
    AutomationState.CANCELLED: [],
    AutomationState.ROLLED_BACK: [],
}

TERMINAL_STATES = {
    AutomationState.COMPLETED,
    AutomationState.FAILED,
    AutomationState.CANCELLED,
    AutomationState.ROLLED_BACK,
}


class StateMachineError(Exception):
    pass


class StateMachine:
    def __init__(self):
        self._state: AutomationState = AutomationState.CREATED
        self._history: list[tuple[AutomationState, float]] = []
        self._record()

    @property
    def state(self) -> AutomationState:
        return self._state

    @property
    def history(self) -> list[tuple[str, float]]:
        return [(s.value, t) for s, t in self._history]

    def can_transition(self, target: AutomationState) -> bool:
        return target in VALID_TRANSITIONS.get(self._state, [])

    def transition(self, target: AutomationState) -> AutomationState:
        if not self.can_transition(target):
            raise StateMachineError(
                f"Invalid transition: {self._state.value} → {target.value}"
            )
        self._state = target
        self._record()
        return self._state

    def is_terminal(self) -> bool:
        return self._state in TERMINAL_STATES

    def is_running(self) -> bool:
        return self._state in (
            AutomationState.RUNNING,
            AutomationState.RETRYING,
        )

    def _record(self):
        import time
        self._history.append((self._state, time.time()))

    def to_dict(self) -> dict:
        return {
            "state": self._state.value,
            "history": self.history,
            "is_terminal": self.is_terminal(),
        }
