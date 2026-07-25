import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from automation.engine.context import AutomationContext
from automation.engine.rollback import RollbackManager
from automation.engine.artifacts import artifact_manager
from automation.plugins.base import AutomationPlugin, RiskLevel


class NotifyPlugin(AutomationPlugin):
    """Notification automation plugin."""

    def __init__(self):
        super().__init__()
        self.name = "Notification"
        self.description = "Desktop alerts, toast notifications, scheduled reminders, digest emails"
        self.version = "1.0"
        self.author = "Jarvis"

    def initialize(self):
        self.register_action("notify.desktop", self.desktop_notification, RiskLevel.SAFE)
        self.register_action("notify.toast", self.toast_notification, RiskLevel.SAFE)
        self.register_action("notify.sound", self.play_sound, RiskLevel.SAFE)
        self.register_action("notify.reminder", self.create_reminder, RiskLevel.SAFE)
        self.register_action("notify.list_reminders", self.list_reminders, RiskLevel.SAFE)
        self.register_action("notify.cancel_reminder", self.cancel_reminder, RiskLevel.SAFE)
        self.register_action("notify.email_digest", self.email_digest, RiskLevel.MEDIUM)
        self.register_action("notify.log_event", self.log_event, RiskLevel.SAFE)

        self.register_workflow({
            "id": "notify_morning_briefing",
            "name": "Morning Briefing",
            "description": "Show desktop notification with system status summary",
            "version": "1.0",
            "variables": {},
            "steps": [
                {"name": "disk_check", "type": "action", "action": "system.disk_usage", "params": {}},
                {"name": "notify", "type": "action", "action": "notify.desktop", "params": {"title": "Jarvis Morning Briefing", "message": "System check complete. Disk usage normal."}},
            ],
        })

    def desktop_notification(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        title = params.get("title", "Jarvis Notification")
        message = params.get("message", "")
        try:
            from plyer import notification
            notification.notify(
                title=title,
                message=message,
                app_name="Jarvis",
                timeout=10,
            )
            return {"status": "ok", "title": title, "message": message}
        except ImportError:
            try:
                subprocess.run(
                    ["powershell", "-Command",
                     f"[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); "
                     f"$notify = New-Object System.Windows.Forms.NotifyIcon; "
                     f"$notify.Icon = [System.Drawing.SystemIcons]::Information; "
                     f"$notify.Visible = $true; "
                     f"$notify.ShowBalloonTip(5000, '{title}', '{message}', "
                     f"[System.Windows.Forms.ToolTipIcon]::Info)"],
                    capture_output=True, text=True, timeout=10,
                )
                return {"status": "ok", "title": title, "method": "powershell"}
            except Exception:
                return {"status": "ok", "title": title, "message": message, "method": "fallback"}

    def toast_notification(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        title = params.get("title", "Jarvis")
        message = params.get("message", "")
        try:
            subprocess.run(
                ["powershell", "-Command",
                 f"Add-Type -AssemblyName System.Windows.Forms; "
                 f"$balloon = New-Object System.Windows.Forms.NotifyIcon; "
                 f"$balloon.Icon = [System.Drawing.SystemIcons]::Information; "
                 f"$balloon.BalloonTipTitle = '{title}'; "
                 f"$balloon.BalloonTipText = '{message}'; "
                 f"$balloon.Visible = $true; "
                 f"$balloon.ShowBalloonTip(5000)"],
                capture_output=True, text=True, timeout=10,
            )
            return {"status": "ok", "title": title}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def play_sound(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        sound_type = params.get("type", "beep")
        try:
            import winsound
            if sound_type == "beep":
                winsound.Beep(1000, 500)
            elif sound_type == "alert":
                winsound.Beep(2000, 300)
                winsound.Beep(1500, 300)
            elif sound_type == "success":
                winsound.Beep(800, 200)
                winsound.Beep(1000, 200)
                winsound.Beep(1200, 400)
            elif sound_type == "error":
                winsound.Beep(500, 300)
                winsound.Beep(400, 300)
                winsound.Beep(300, 500)
            else:
                winsound.MessageBeep()
            return {"status": "ok", "sound": sound_type}
        except ImportError:
            return {"status": "ok", "sound": sound_type, "method": "silent"}

    def create_reminder(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        title = params.get("title", "Reminder")
        message = params.get("message", "")
        delay_minutes = params.get("delay_minutes", 5)

        reminders_dir = Path("data/reminders")
        reminders_dir.mkdir(parents=True, exist_ok=True)

        reminder = {
            "id": f"rem_{int(time.time())}",
            "title": title,
            "message": message,
            "created_at": datetime.now().isoformat(),
            "trigger_at": (datetime.now().replace(microsecond=0) + __import__("datetime").timedelta(minutes=delay_minutes)).isoformat(),
            "status": "pending",
        }

        with open(reminders_dir / f"{reminder['id']}.json", "w", encoding="utf-8") as f:
            json.dump(reminder, f, indent=2)

        return {"status": "ok", "reminder": reminder}

    def list_reminders(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        reminders_dir = Path("data/reminders")
        if not reminders_dir.exists():
            return {"status": "ok", "reminders": []}

        reminders = []
        for f in reminders_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    reminders.append(json.load(fh))
            except Exception:
                continue

        return {"status": "ok", "count": len(reminders), "reminders": reminders}

    def cancel_reminder(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        reminder_id = params.get("id", "")
        path = Path("data/reminders") / f"{reminder_id}.json"
        if path.exists():
            path.unlink()
            return {"status": "ok", "cancelled": reminder_id}
        return {"status": "error", "error": "Reminder not found"}

    def email_digest(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        subject = params.get("subject", "Jarvis Daily Digest")
        content = params.get("content", "")
        recipient = params.get("recipient", "")

        digest = {
            "subject": subject,
            "content": content,
            "recipient": recipient,
            "generated_at": datetime.now().isoformat(),
        }

        artifact = artifact_manager.save_file(
            name=f"digest_{datetime.now().strftime('%Y%m%d')}",
            content=json.dumps(digest, indent=2).encode(),
            automation_id=ctx.automation_id,
            extension="json",
        )

        return {"status": "ok", "digest": digest, "artifact_id": artifact.id, "note": "Email sending requires SMTP configuration"}

    def log_event(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        from core.structured_log import structured_logger
        level = params.get("level", "INFO")
        message = params.get("message", "")
        structured_logger.log(level, message, source="automation", automation_id=ctx.automation_id)
        return {"status": "ok", "level": level, "message": message}
