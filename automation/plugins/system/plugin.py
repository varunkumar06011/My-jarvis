import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from automation.engine.context import AutomationContext
from automation.engine.rollback import RollbackManager
from automation.engine.artifacts import artifact_manager
from automation.plugins.base import AutomationPlugin, RiskLevel


class SystemPlugin(AutomationPlugin):
    """System maintenance automation plugin."""

    def __init__(self):
        super().__init__()
        self.name = "System"
        self.description = "System maintenance: cleanup temp, disk check, service check, startup manage"
        self.version = "1.0"
        self.author = "Jarvis"

    def initialize(self):
        self.register_action("system.cleanup_temp", self.cleanup_temp, RiskLevel.MEDIUM, requires_rollback=True)
        self.register_action("system.disk_usage", self.disk_usage, RiskLevel.SAFE)
        self.register_action("system.disk_cleanup", self.disk_cleanup, RiskLevel.HIGH)
        self.register_action("system.list_services", self.list_services, RiskLevel.SAFE)
        self.register_action("system.service_status", self.service_status, RiskLevel.SAFE)
        self.register_action("system.start_service", self.start_service, RiskLevel.HIGH)
        self.register_action("system.stop_service", self.stop_service, RiskLevel.HIGH)
        self.register_action("system.list_startup", self.list_startup, RiskLevel.SAFE)
        self.register_action("system.enable_startup", self.enable_startup, RiskLevel.HIGH)
        self.register_action("system.disable_startup", self.disable_startup, RiskLevel.MEDIUM)
        self.register_action("system.system_info", self.system_info, RiskLevel.SAFE)
        self.register_action("system.network_info", self.network_info, RiskLevel.SAFE)
        self.register_action("system.env_vars", self.env_vars, RiskLevel.SAFE)
        self.register_action("system.kill_process", self.kill_process, RiskLevel.HIGH)
        self.register_action("system.create_restore_point", self.create_restore_point, RiskLevel.CRITICAL)

        self.register_workflow({
            "id": "system_daily_maintenance",
            "name": "System Daily Maintenance",
            "description": "Check disk, cleanup temp, list services",
            "version": "1.0",
            "variables": {},
            "steps": [
                {"name": "disk_check", "type": "action", "action": "system.disk_usage", "params": {}},
                {"name": "cleanup", "type": "action", "action": "system.cleanup_temp", "params": {}},
                {"name": "services", "type": "action", "action": "system.list_services", "params": {}},
                {"name": "network", "type": "action", "action": "system.network_info", "params": {}},
            ],
        })

    def _run_ps(self, command: str, timeout: int = 30) -> dict:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True, text=True, timeout=timeout,
            )
            return {"exit_code": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
        except Exception as e:
            return {"exit_code": -1, "stdout": "", "stderr": str(e)}

    def cleanup_temp(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        temp_dir = Path(tempfile.gettempdir())
        deleted = 0
        freed_bytes = 0
        for item in temp_dir.iterdir():
            try:
                size = item.stat().st_size if item.is_file() else 0
                if item.is_file():
                    item.unlink()
                    deleted += 1
                    freed_bytes += size
                elif item.is_dir() and "jarvis" not in item.name.lower():
                    shutil.rmtree(item, ignore_errors=True)
                    deleted += 1
            except Exception:
                continue
        return {"status": "ok", "deleted": deleted, "freed_mb": round(freed_bytes / 1024 / 1024, 2)}

    def disk_usage(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        import shutil as sh
        total, used, free = sh.disk_usage("/")
        return {
            "status": "ok",
            "total_gb": round(total / 1024**3, 2),
            "used_gb": round(used / 1024**3, 2),
            "free_gb": round(free / 1024**3, 2),
            "percent_used": round(used / total * 100, 1),
        }

    def disk_cleanup(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        r = self._run_ps("cleanmgr /sagerun:1", timeout=120)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"] or r["stderr"]}

    def list_services(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        r = self._run_ps("Get-Service | Select-Object Name,Status,StartType | ConvertTo-Json", timeout=30)
        import json
        try:
            services = json.loads(r["stdout"])
            if isinstance(services, dict):
                services = [services]
            result = [{"name": s.get("Name"), "status": s.get("Status"), "start_type": s.get("StartType")} for s in services[:50]]
            return {"status": "ok", "count": len(result), "services": result}
        except Exception:
            return {"status": "ok", "count": 0, "services": []}

    def service_status(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        name = params.get("name", "")
        r = self._run_ps(f"Get-Service -Name '{name}' | Select-Object Name,Status,StartType | ConvertTo-Json")
        import json
        try:
            s = json.loads(r["stdout"])
            return {"status": "ok", "name": s.get("Name"), "state": s.get("Status"), "start_type": s.get("StartType")}
        except Exception:
            return {"status": "error", "error": "Service not found"}

    def start_service(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        name = params.get("name", "")
        r = self._run_ps(f"Start-Service -Name '{name}'")
        rollback.register("system.stop_service", lambda: self._run_ps(f"Stop-Service -Name '{name}'"), f"Stop {name}")
        return {"status": "ok" if r["exit_code"] == 0 else "error", "service": name}

    def stop_service(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        name = params.get("name", "")
        r = self._run_ps(f"Stop-Service -Name '{name}' -Force")
        return {"status": "ok" if r["exit_code"] == 0 else "error", "service": name}

    def list_startup(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        r = self._run_ps(
            "Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location | ConvertTo-Json"
        )
        import json
        try:
            items = json.loads(r["stdout"])
            if isinstance(items, dict):
                items = [items]
            result = [{"name": i.get("Name"), "command": i.get("Command"), "location": i.get("Location")} for i in items]
            return {"status": "ok", "count": len(result), "startup_items": result}
        except Exception:
            return {"status": "ok", "count": 0, "startup_items": []}

    def enable_startup(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        name = params.get("name", "")
        command = params.get("command", "")
        r = self._run_ps(f"New-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run' -Name '{name}' -Value '{command}' -PropertyType String -Force")
        return {"status": "ok" if r["exit_code"] == 0 else "error", "name": name}

    def disable_startup(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        name = params.get("name", "")
        r = self._run_ps(f"Remove-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run' -Name '{name}' -ErrorAction SilentlyContinue")
        return {"status": "ok", "name": name}

    def system_info(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        r = self._run_ps("Get-ComputerInfo | Select-Object CsName,WindowsVersion,OsArchitecture,CsProcessors,CsTotalPhysicalMemory | ConvertTo-Json")
        import json
        try:
            info = json.loads(r["stdout"])
            return {"status": "ok", "info": info}
        except Exception:
            return {"status": "ok", "info": {}}

    def network_info(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        r = self._run_ps("Get-NetIPConfiguration | Select-Object InterfaceAlias,IPv4Address | ConvertTo-Json")
        import json
        try:
            info = json.loads(r["stdout"])
            if isinstance(info, dict):
                info = [info]
            return {"status": "ok", "interfaces": info}
        except Exception:
            return {"status": "ok", "interfaces": []}

    def env_vars(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        return {"status": "ok", "vars": dict(os.environ)}

    def kill_process(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        pid = params.get("pid", 0)
        name = params.get("name", "")
        if pid:
            r = self._run_ps(f"Stop-Process -Id {pid} -Force")
        elif name:
            r = self._run_ps(f"Stop-Process -Name '{name}' -Force")
        else:
            return {"status": "error", "error": "Need pid or name"}
        return {"status": "ok" if r["exit_code"] == 0 else "error"}

    def create_restore_point(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        description = params.get("description", "Jarvis Restore Point")
        r = self._run_ps(
            f"Checkpoint-Computer -Description '{description}' -RestorePointType 'MODIFY_SETTINGS'"
        )
        return {"status": "ok" if r["exit_code"] == 0 else "error", "description": description}
