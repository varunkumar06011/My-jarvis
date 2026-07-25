import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from ai.cto.dashboard import executive_dashboard, REPORTS_DIR
from core.event_store import event_store
from core.metrics import metrics
from core.telemetry import telemetry


class ReportGenerator:
    def __init__(self):
        self._reports: list[dict] = []

    def generate_daily(self) -> dict:
        snap = executive_dashboard.snapshot()
        report = {
            "id": f"daily-{datetime.now().strftime('%Y%m%d')}",
            "type": "daily",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "period": "last_24h",
            "data": snap,
        }
        self._save(report)
        return report

    def generate_weekly(self) -> dict:
        snap = executive_dashboard.snapshot()
        stats = event_store.statistics()
        tel = telemetry.summary()
        perf = metrics.performance_summary()

        report = {
            "id": f"weekly-{datetime.now().strftime('%Y%m%d')}",
            "type": "weekly",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "period": "last_7_days",
            "data": {
                "summary": snap,
                "event_trends": stats,
                "telemetry_trends": tel,
                "performance_trends": perf,
                "recommendations": self._generate_recommendations(snap),
            },
        }
        self._save(report)
        return report

    def generate_monthly(self) -> dict:
        snap = executive_dashboard.snapshot()
        stats = event_store.statistics()

        report = {
            "id": f"monthly-{datetime.now().strftime('%Y%m%d')}",
            "type": "monthly",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "period": "last_30_days",
            "data": {
                "summary": snap,
                "event_statistics": stats,
                "recommendations": self._generate_recommendations(snap),
                "milestones": [],
            },
        }
        self._save(report)
        return report

    def _generate_recommendations(self, snapshot: dict) -> list[dict]:
        recs = []

        health = snapshot.get("project_health", {})
        for issue in health.get("issues", []):
            recs.append({
                "priority": "high" if issue.get("severity") == "high" else "medium",
                "category": "health",
                "message": issue.get("message", ""),
                "action": f"Investigate {issue.get('service', 'unknown')} service",
            })

        for risk in health.get("security_risks", []):
            recs.append({
                "priority": "high",
                "category": "security",
                "message": risk.get("message", ""),
                "action": "Update configuration immediately",
            })

        for reg in health.get("performance_regressions", []):
            recs.append({
                "priority": "medium",
                "category": "performance",
                "message": f"{reg.get('operation', '?')} P95: {reg.get('p95_ms', 0)}ms",
                "action": "Profile and optimize slow operation",
            })

        sys_status = snapshot.get("system_status", {})
        if sys_status.get("ram_percent", 0) > 80:
            recs.append({
                "priority": "high",
                "category": "resources",
                "message": f"Memory usage at {sys_status['ram_percent']:.1f}%",
                "action": "Consider restarting services or increasing RAM",
            })

        if sys_status.get("cpu_percent", 0) > 80:
            recs.append({
                "priority": "high",
                "category": "resources",
                "message": f"CPU usage at {sys_status['cpu_percent']:.1f}%",
                "action": "Reduce concurrent operations or upgrade hardware",
            })

        return recs

    def _save(self, report: dict):
        filepath = REPORTS_DIR / f"{report['id']}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        self._reports.append({"id": report["id"], "type": report["type"], "path": str(filepath)})
        print(f"[CTO] Report saved: {filepath}")

    def list_reports(self) -> list[dict]:
        reports = []
        for f in sorted(REPORTS_DIR.glob("*.json"), reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                reports.append({
                    "id": data.get("id", f.stem),
                    "type": data.get("type", "unknown"),
                    "generated_at": data.get("generated_at", ""),
                    "path": str(f),
                })
            except Exception:
                continue
        return reports

    def get_report(self, report_id: str) -> Optional[dict]:
        filepath = REPORTS_DIR / f"{report_id}.json"
        if not filepath.exists():
            return None
        return json.loads(filepath.read_text(encoding="utf-8"))


report_generator = ReportGenerator()
