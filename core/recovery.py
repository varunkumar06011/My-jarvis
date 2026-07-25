import threading
import time
from collections import defaultdict
from typing import Callable, Optional

from core.event_bus import bus
from core.service_registry import registry


class RecoveryAction:
    RESTART = "restart"
    NOTIFY = "notify"
    DISABLE = "disable"
    ESCALATE = "escalate"


class RecoveryRule:
    def __init__(
        self,
        service: str,
        max_retries: int = 3,
        cooldown_seconds: float = 30,
        action: str = RecoveryAction.RESTART,
        restart_fn: Optional[Callable] = None,
    ):
        self.service = service
        self.max_retries = max_retries
        self.cooldown_seconds = cooldown_seconds
        self.action = action
        self.restart_fn = restart_fn
        self._retry_count = 0
        self._last_retry = 0


class RecoveryEngine:
    def __init__(self):
        self._rules: dict[str, RecoveryRule] = {}
        self._lock = threading.Lock()
        self._running = False
        self._recovery_log: list[dict] = []

    def register_rule(
        self,
        service: str,
        max_retries: int = 3,
        cooldown_seconds: float = 30,
        restart_fn: Optional[Callable] = None,
    ):
        rule = RecoveryRule(
            service=service,
            max_retries=max_retries,
            cooldown_seconds=cooldown_seconds,
            restart_fn=restart_fn,
        )
        with self._lock:
            self._rules[service] = rule

    def start(self):
        if self._running:
            return
        self._running = True
        bus.subscribe("HealthCheckFailed", self._on_health_failed)
        bus.subscribe("TaskFailed", self._on_task_failed)
        print("[Recovery] Engine started")

    def stop(self):
        self._running = False

    def _on_health_failed(self, data: dict):
        if not data:
            return
        service = data.get("service", "")
        self._attempt_recovery(service, "health_check_failed")

    def _on_task_failed(self, data: dict):
        if not data:
            return
        name = data.get("name", "")
        if name.startswith("tool:"):
            tool_name = name.replace("tool:", "")
            self._attempt_recovery(f"plugin:{tool_name}", "task_failed")

    def _attempt_recovery(self, service: str, reason: str):
        with self._lock:
            rule = self._rules.get(service)

        if rule is None:
            return

        now = time.time()

        if rule._retry_count >= rule.max_retries:
            self._log_recovery(service, RecoveryAction.ESCALATE, reason, "Max retries exceeded")
            bus.publish("RecoveryEscalated", {"service": service, "reason": reason})
            return

        if now - rule._last_retry < rule.cooldown_seconds:
            return

        rule._retry_count += 1
        rule._last_retry = now

        if rule.action == RecoveryAction.RESTART and rule.restart_fn:
            try:
                rule.restart_fn()
                self._log_recovery(service, RecoveryAction.RESTART, reason, "Restarted successfully")
                bus.publish("RecoverySucceeded", {"service": service, "reason": reason})
                rule._retry_count = 0
            except Exception as e:
                self._log_recovery(service, RecoveryAction.RESTART, reason, f"Restart failed: {e}")
                bus.publish("RecoveryFailed", {"service": service, "error": str(e)})
        elif rule.action == RecoveryAction.NOTIFY:
            self._log_recovery(service, RecoveryAction.NOTIFY, reason, "Notified")
            bus.publish("RecoveryNotified", {"service": service, "reason": reason})

    def _log_recovery(self, service: str, action: str, reason: str, result: str):
        entry = {
            "timestamp": time.time(),
            "service": service,
            "action": action,
            "reason": reason,
            "result": result,
        }
        self._recovery_log.append(entry)
        if len(self._recovery_log) > 200:
            self._recovery_log = self._recovery_log[-200:]
        print(f"[Recovery] {action} → {service}: {result}")

    def get_recovery_log(self) -> list[dict]:
        return list(self._recovery_log)

    def get_rules(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "service": r.service,
                    "max_retries": r.max_retries,
                    "cooldown_seconds": r.cooldown_seconds,
                    "action": r.action,
                    "retry_count": r._retry_count,
                }
                for r in self._rules.values()
            ]


recovery_engine = RecoveryEngine()
