import threading
import time

from core.event_bus import bus


class HealthManager:
    def __init__(self, check_interval=30):
        self.check_interval = check_interval
        self._checks = {}
        self._running = False
        self._thread = None

    def register_check(self, name, check_fn):
        self._checks[name] = check_fn

    def run_check(self, name):
        check_fn = self._checks.get(name)
        if check_fn is None:
            return False
        try:
            return check_fn()
        except Exception:
            return False

    def run_all_checks(self):
        results = {}
        for name, check_fn in self._checks.items():
            try:
                results[name] = check_fn()
            except Exception:
                results[name] = False
        return results

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            time.sleep(self.check_interval)
            results = self.run_all_checks()

            for name, healthy in results.items():
                if not healthy:
                    bus.publish("HealthCheckFailed", {"service": name})
                    print(f"[Health] ⚠ {name} check failed")
                else:
                    bus.publish("HealthCheckPassed", {"service": name})


health = HealthManager()
