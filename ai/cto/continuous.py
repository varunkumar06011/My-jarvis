"""Continuous AI CTO — background monitor that periodically collects project health
metrics, generates reports, and publishes CTO-level insights and recommendations."""

import threading
import time
from datetime import datetime
from typing import Optional

from core.event_bus import bus
from logs.logger import write_log


class ContinuousCTO:
    """Runs a background thread that periodically collects dashboard snapshots,
    detects health changes, and publishes CTO insights."""

    def __init__(self, interval_seconds: int = 300):
        self.interval = interval_seconds
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._last_snapshot: dict = {}
        self._last_report_time: Optional[str] = None

    def start(self):
        """Start the continuous CTO monitoring thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="ContinuousCTO")
        self._thread.start()
        write_log("AI_CTO", f"Continuous CTO monitoring started (interval: {self.interval}s)")
        bus.publish("ContinuousCTOStarted", {"interval": self.interval})

    def stop(self):
        """Stop the continuous CTO monitoring thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        write_log("AI_CTO", "Continuous CTO monitoring stopped")
        bus.publish("ContinuousCTOStopped", {})

    def _loop(self):
        while self._running:
            try:
                self._monitor()
            except Exception as e:
                write_log("AI_CTO", f"Monitor error: {e}")
            time.sleep(self.interval)

    def _monitor(self):
        """Collect snapshot, detect changes, and publish insights."""
        try:
            from ai.cto.dashboard import executive_dashboard
            snapshot = executive_dashboard.snapshot()
        except Exception as e:
            write_log("AI_CTO", f"Snapshot failed: {e}")
            return

        # Detect changes since last snapshot
        changes = self._detect_changes(self._last_snapshot, snapshot)
        self._last_snapshot = snapshot

        if changes:
            bus.publish("CTOHealthChanged", {
                "changes": changes,
                "timestamp": datetime.now().isoformat(),
            })
            write_log("AI_CTO", f"Health changes detected: {len(changes)} items")

        # Check for critical issues
        health = snapshot.get("project_health", {})
        issues = health.get("issues", [])
        critical_issues = [i for i in issues if i.get("severity") == "critical"]

        if critical_issues:
            bus.publish("CTOCriticalAlert", {
                "issues": critical_issues,
                "count": len(critical_issues),
                "timestamp": datetime.now().isoformat(),
            })
            write_log("AI_CTO", f"Critical alert: {len(critical_issues)} critical issues")

        # Periodic report generation (every hour)
        now = datetime.now()
        if self._last_report_time is None or self._hours_since(self._last_report_time) >= 1:
            self._generate_hourly_report(snapshot)
            self._last_report_time = now.isoformat()

        # Publish heartbeat
        bus.publish("CTOMonitorCompleted", {
            "timestamp": now.isoformat(),
            "issues_count": len(issues),
            "critical_count": len(critical_issues),
        })

    def _detect_changes(self, old: dict, new: dict) -> list:
        """Detect changes between two snapshots."""
        if not old:
            return []

        changes = []

        # Compare project health issues
        old_issues = set()
        for issue in old.get("project_health", {}).get("issues", []):
            old_issues.add(issue.get("description", ""))

        new_issues = new.get("project_health", {}).get("issues", [])
        for issue in new_issues:
            desc = issue.get("description", "")
            if desc and desc not in old_issues:
                changes.append({"type": "new_issue", "description": desc, "severity": issue.get("severity", "info")})

        # Compare service health
        old_services = old.get("service_health", {})
        new_services = new.get("service_health", {})
        for svc_name, svc_status in new_services.items():
            old_status = old_services.get(svc_name, {}).get("status")
            if old_status and old_status != svc_status.get("status"):
                changes.append({
                    "type": "service_status_changed",
                    "service": svc_name,
                    "old": old_status,
                    "new": svc_status.get("status"),
                })

        # Compare event statistics
        old_events = old.get("event_stats", {}).get("total", 0)
        new_events = new.get("event_stats", {}).get("total", 0)
        if new_events > old_events:
            changes.append({
                "type": "events_increased",
                "delta": new_events - old_events,
                "total": new_events,
            })

        return changes

    def _generate_hourly_report(self, snapshot: dict):
        """Generate and save an hourly CTO report."""
        try:
            from ai.cto.dashboard import ReportGenerator
            report_gen = ReportGenerator()
            report = report_gen.generate_daily()

            bus.publish("CTOReportGenerated", {
                "report_id": report.get("id", "unknown"),
                "timestamp": datetime.now().isoformat(),
            })
            write_log("AI_CTO", f"Hourly report generated: {report.get('id', 'unknown')}")
        except Exception as e:
            write_log("AI_CTO", f"Report generation failed: {e}")

    def _hours_since(self, iso_time: str) -> float:
        """Calculate hours since a given ISO timestamp."""
        try:
            then = datetime.fromisoformat(iso_time)
            return (datetime.now() - then).total_seconds() / 3600
        except Exception:
            return 999.0

    def get_status(self) -> dict:
        """Get current status of the continuous CTO monitor."""
        return {
            "running": self._running,
            "interval": self.interval,
            "last_report_time": self._last_report_time,
            "last_snapshot_keys": list(self._last_snapshot.keys()) if self._last_snapshot else [],
        }


continuous_cto = ContinuousCTO()
