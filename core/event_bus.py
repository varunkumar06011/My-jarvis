from collections import defaultdict
from threading import Lock


class EventBus:
    def __init__(self):
        self._subscribers = defaultdict(list)
        self._lock = Lock()

    def subscribe(self, event_type, callback):
        with self._lock:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type, callback):
        with self._lock:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)

    def publish(self, event_type, data=None):
        with self._lock:
            callbacks = list(self._subscribers[event_type])

        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                print(f"[EventBus] Error in handler for {event_type}: {e}")

    def clear(self):
        with self._lock:
            self._subscribers.clear()


bus = EventBus()
