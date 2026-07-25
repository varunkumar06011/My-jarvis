import ast
import json
import os
import subprocess
import sys
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

        # Failed builds — check event store for failed automation tasks
        events = event_store.search(event_type="TaskFailed", limit=20)
        for evt in events:
            health_data.failed_builds.append({
                "task": evt.get("data", {}).get("name", "unknown"),
                "error": evt.get("data", {}).get("error", ""),
                "timestamp": evt.get("timestamp", ""),
            })

        # Technical debt — scan for TODO/FIXME in Python files
        health_data.tech_debt = self._scan_tech_debt()

        # Pending releases — check for git tags or release-related events
        health_data.pending_releases = self._check_pending_releases()

        # Test coverage — integrate with pytest-cov if available
        health_data.test_coverage = self._collect_test_coverage()

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

    def _scan_tech_debt(self) -> list[dict]:
        debt = []
        root = Path(".")
        exclude = {"venv", "__pycache__", ".git", "node_modules", "assets", "data"}
        count = 0
        for f in root.rglob("*.py"):
            if any(part in exclude for part in f.parts):
                continue
            try:
                lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if "TODO" in stripped or "FIXME" in stripped or "HACK" in stripped:
                        debt.append({
                            "file": str(f.relative_to(root)).replace("\\", "/"),
                            "line": i,
                            "type": "TODO" if "TODO" in stripped else ("FIXME" if "FIXME" in stripped else "HACK"),
                            "text": stripped[:100],
                        })
                        count += 1
                        if count >= 50:
                            return debt
            except Exception:
                continue
        return debt

    def _check_pending_releases(self) -> list[dict]:
        releases = []
        try:
            result = subprocess.run(
                ["git", "tag", "--sort=-creatordate"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                tags = result.stdout.strip().splitlines()[:5]
                for tag in tags:
                    releases.append({"tag": tag, "status": "released"})

            result = subprocess.run(
                ["git", "log", "--oneline", "-10"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                commits = result.stdout.strip().splitlines()
                for commit in commits:
                    if any(kw in commit.lower() for kw in ["release", "version", "v1."]):
                        releases.append({"commit": commit[:80], "status": "pending"})
        except Exception:
            pass
        return releases[:10]

    def _collect_test_coverage(self) -> dict:
        coverage_file = Path(".coverage")
        if not coverage_file.exists():
            return {
                "status": "not_available",
                "note": "Run 'python -m pytest --cov' to generate coverage data",
            }

        try:
            import coverage
            cov = coverage.Coverage()
            cov.load()
            analysis = cov.analysis2
            total_lines = 0
            covered_lines = 0
            files = {}

            for filename in cov.get_data().measured_files():
                try:
                    _, statements, missing, _ = cov.analysis(filename)
                    total = len(statements)
                    covered = total - len(missing)
                    total_lines += total
                    covered_lines += covered
                    rel = str(Path(filename).relative_to(Path(".").resolve())).replace("\\", "/")
                    files[rel] = {
                        "total": total,
                        "covered": covered,
                        "missing": len(missing),
                        "percent": round(covered / total * 100, 1) if total > 0 else 0,
                    }
                except Exception:
                    continue

            percent = round(covered_lines / total_lines * 100, 1) if total_lines > 0 else 0
            return {
                "status": "available",
                "percent": percent,
                "covered_lines": covered_lines,
                "total_lines": total_lines,
                "files": dict(list(files.items())[:20]),
            }
        except ImportError:
            return {
                "status": "not_configured",
                "note": "Install pytest-cov: pip install pytest-cov",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }


executive_dashboard = ExecutiveDashboard()
