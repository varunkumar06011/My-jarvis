import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from ai.cto.dashboard import executive_dashboard, REPORTS_DIR
from core.event_store import event_store
from core.metrics import metrics
from core.telemetry import telemetry


MILESTONES_FILE = REPORTS_DIR / "milestones.json"


class MilestoneTracker:
    def __init__(self):
        self._milestones: list[dict] = []
        self._load()

    def _load(self):
        if MILESTONES_FILE.exists():
            try:
                self._milestones = json.loads(MILESTONES_FILE.read_text(encoding="utf-8"))
            except Exception:
                self._milestones = []

    def _save(self):
        MILESTONES_FILE.write_text(json.dumps(self._milestones, indent=2, ensure_ascii=False), encoding="utf-8")

    def add(self, title: str, description: str = "", category: str = "general",
            target_date: str = "", status: str = "planned") -> dict:
        milestone = {
            "id": f"ms-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "title": title,
            "description": description,
            "category": category,
            "target_date": target_date,
            "status": status,
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
        }
        self._milestones.append(milestone)
        self._save()
        return milestone

    def complete(self, milestone_id: str) -> dict:
        for ms in self._milestones:
            if ms["id"] == milestone_id:
                ms["status"] = "completed"
                ms["completed_at"] = datetime.now().isoformat()
                self._save()
                return ms
        return {"error": "Milestone not found"}

    def list(self, status: str = "", category: str = "", limit: int = 50) -> List[dict]:
        results = []
        for ms in self._milestones:
            if status and ms.get("status") != status:
                continue
            if category and ms.get("category") != category:
                continue
            results.append(ms)
        return results[-limit:]

    def get_monthly_milestones(self, year: int = None, month: int = None) -> List[dict]:
        now = datetime.now()
        year = year or now.year
        month = month or now.month
        results = []
        for ms in self._milestones:
            created = ms.get("created_at", "")[:10]
            completed = ms.get("completed_at", "")[:10] if ms.get("completed_at") else ""
            target = ms.get("target_date", "")[:10] if ms.get("target_date") else ""

            for date_str in [created, completed, target]:
                if date_str and str(year) in date_str:
                    month_part = int(date_str.split("-")[1]) if "-" in date_str else 0
                    if month_part == month:
                        results.append(ms)
                        break
        return results

    def auto_generate_from_events(self) -> List[dict]:
        events = event_store.search(limit=100)
        auto = []

        completed_tasks = [e for e in events if e.get("event_type") == "TaskCompleted"]
        if len(completed_tasks) >= 5:
            auto.append({
                "title": f"{len(completed_tasks)} tasks completed",
                "category": "automation",
                "status": "completed",
            })

        automation_events = [e for e in events if "Automation" in e.get("event_type", "")]
        if automation_events:
            auto.append({
                "title": f"{len(automation_events)} automation events",
                "category": "automation",
                "status": "completed",
            })

        health_events = [e for e in events if e.get("event_type") in ("HealthCheckPassed", "HealthCheckFailed")]
        if health_events:
            passed = sum(1 for e in health_events if e.get("event_type") == "HealthCheckPassed")
            auto.append({
                "title": f"Health checks: {passed}/{len(health_events)} passed",
                "category": "health",
                "status": "completed",
            })

        return auto


milestone_tracker = MilestoneTracker()


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

        auto_milestones = milestone_tracker.auto_generate_from_events()
        recorded_milestones = milestone_tracker.get_monthly_milestones()
        all_milestones = auto_milestones + [m for m in recorded_milestones if m not in auto_milestones]

        report = {
            "id": f"monthly-{datetime.now().strftime('%Y%m%d')}",
            "type": "monthly",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "period": "last_30_days",
            "data": {
                "summary": snap,
                "event_statistics": stats,
                "recommendations": self._generate_recommendations(snap),
                "milestones": all_milestones,
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
