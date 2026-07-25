from enum import Enum


class State(Enum):
    STARTING = "Starting"
    READY = "Ready"
    LISTENING = "Listening"
    PROCESSING = "Processing"
    SPEAKING = "Speaking"
    IDLE = "Idle"
    SHUTDOWN = "Shutdown"


class LifecycleManager:
    def __init__(self):
        self._state = State.STARTING
        self._listeners = []

    @property
    def state(self):
        return self._state

    def transition(self, new_state):
        old_state = self._state
        self._state = new_state
        print(f"[Lifecycle] {old_state.value} -> {new_state.value}")
        for listener in self._listeners:
            listener(old_state, new_state)

    def on_change(self, callback):
        self._listeners.append(callback)

    def is_running(self):
        return self._state != State.SHUTDOWN
