import json
import os
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from core.service_registry import registry
from core.event_bus import bus
from core.event_store import event_store
from core.metrics import metrics
from core.telemetry import telemetry
from core.health_manager import health


REPORTS_DIR = Path("data/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class ProjectHealth:
    def __init__(self):
        self.issues: list[dict] = []
        self.failed_builds: list[dict] = []
        self.tech_debt: list[dict] = []
        self.security_risks: list[dict] = []
        self.perf_regressions: list[dict] = []
        self.test_coverage: dict = {}
        self.pending_releases: list[dict] = []

    def to_dict(self) -> dict:
        return {
            "issues": self.issues,
            "failed_builds": self.failed_builds,
            "tech_debt": self.tech_debt,
            "security_risks": self.security_risks,
            "performance_regressions": self.perf_regressions,
            "test_coverage": self.test_coverage,
            "pending_releases": self.pending_releases,
        }


class ExecutiveDashboard:
    def __init__(self):
        self._lock = threading.Lock()
        self._last_snapshot: Optional[dict] = None
        self._last_updated: float = 0

    def snapshot(self) -> dict:
        now = time.time()

        with self._lock:
            if self._last_snapshot and (now - self._last_updated) < 5:
                return self._last_snapshot

        snap = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "project_health": self._collect_project_health(),
            "system_status": self._collect_system_status(),
            "service_health": self._collect_service_health(),
            "event_statistics": event_store.statistics(),
            "telemetry_summary": telemetry.summary(),
            "performance": metrics.performance_summary(),
            "automation_summary": self._collect_automation_summary(),
            "uptime": self._collect_uptime(),
        }

        with self._lock:
            self._last_snapshot = snap
            self._last_updated = now

        return snap

    def _collect_project_health(self) -> dict:
        health_data = ProjectHealth()

        # Check for failed health checks
        results = health.run_all_checks()
        for name, ok in results.items():
            if not ok:
                health_data.issues.append({
                    "service": name,
                    "severity": "high",
                    "message": f"Health check failed for {name}",
                })

        # Check telemetry for errors
        tel_summary = telemetry.summary()
        for category, count in tel_summary.get("error_counts", {}).items():
            if count > 0:
                health_data.issues.append({
                    "service": category,
                    "severity": "medium",
                    "message": f"{count} errors in {category}",
                })

        # Check for security risks (basic checks)
        from configs.config import API_DEFAULT_KEY, API_JWT_SECRET
        if API_DEFAULT_KEY == "jarvis-local-dev-key":
            health_data.security_risks.append({
                "severity": "high",
                "message": "Default API key in use — change JARVIS_API_DEFAULT_KEY",
            })
        if API_JWT_SECRET == "jarvis-jwt-secret-change-in-production":
            health_data.security_risks.append({
                "severity": "high",
                "message": "Default JWT secret in use — change JARVIS_JWT_SECRET",
            })

        # Check for performance regressions
        perf = metrics.performance_summary()
        for op, data in perf.items():
            if isinstance(data, dict) and data.get("p95_ms", 0) > 5000:
                health_data.perf_regressions.append({
                    "operation": op,
                    "p95_ms": data["p95_ms"],
                    "severity": "medium",
                })

        # Test coverage (placeholder — would integrate with pytest-cov)
        health_data.test_coverage = {
            "status": "not_configured",
            "note": "Install pytest-cov and run tests for coverage data",
        }

        return health_data.to_dict()

    def _collect_system_status(self) -> dict:
        perf = metrics.performance_summary()
        return {
            "cpu_percent": perf.get("cpu_percent", 0),
            "ram_percent": perf.get("ram_percent", 0),
            "ram_used_mb": round(perf.get("ram_used_mb", 0), 1),
            "disk_percent": perf.get("disk_percent", 0),
            "thread_count": perf.get("thread_count", 0),
        }

    def _collect_service_health(self) -> dict:
        results = health.run_all_checks()
        return {
            "total_services": len(registry.list_services()),
            "healthy": sum(1 for ok in results.values() if ok),
            "unhealthy": sum(1 for ok in results.values() if not ok),
            "details": {name: "healthy" if ok else "unhealthy" for name, ok in results.items()},
        }

    def _collect_automation_summary(self) -> dict:
        if registry.has("automation_engine"):
            engine = registry.get("automation_engine")
            try:
                return {
                    "history": engine.get_history_summary(),
                    "queue": engine.get_queue_status(),
                    "active": len(engine.list_active()),
                    "pending_approvals": len(engine.get_pending_approvals()),
                }
            except Exception:
                pass
        return {"status": "not_available"}

    def _collect_uptime(self) -> dict:
        if registry.has("lifecycle"):
            lc = registry.get("lifecycle")
            return {
                "state": lc.state.value,
                "running": lc.is_running(),
            }
        return {"state": "unknown"}


executive_dashboard = ExecutiveDashboard()
