import os
import subprocess
import time
from typing import Any, Optional

from automation.engine.context import AutomationContext
from automation.engine.rollback import RollbackManager
from automation.engine.artifacts import artifact_manager


class WindowsAutomation:
    """Windows OS automation: apps, processes, clipboard, screenshots, etc."""

    def launch_app(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        app = params.get("app", "")
        args = params.get("args", [])
        cmd = [app] + args if isinstance(args, list) else [app]
        proc = subprocess.Popen(cmd, shell=False)
        rollback.register(
            "windows.close_app",
            lambda: self._kill_pid(proc.pid),
            f"Kill process {app} (pid={proc.pid})",
        )
        return {"status": "launched", "app": app, "pid": proc.pid}

    def close_app(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        app_name = params.get("app", "")
        result = subprocess.run(
            ["taskkill", "/IM", app_name, "/F"],
            capture_output=True, text=True, timeout=10,
        )
        return {"status": "closed", "app": app_name, "output": result.stdout.strip()}

    def _kill_pid(self, pid: int):
        try:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=10)
        except Exception:
            pass

    def list_processes(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV"],
            capture_output=True, text=True, timeout=10,
        )
        lines = result.stdout.strip().split("\n")
        processes = []
        for line in lines[1:]:
            parts = line.strip('"').split('","')
            if len(parts) >= 2:
                processes.append({"name": parts[0], "pid": parts[1]})
        return {"status": "ok", "count": len(processes), "processes": processes[:50]}

    def clipboard_get(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            data = win32clipboard.GetClipboardData()
            win32clipboard.CloseClipboard()
            return {"status": "ok", "content": data}
        except ImportError:
            return {"status": "error", "error": "pywin32 not installed"}

    def clipboard_set(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        text = params.get("text", "")
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text)
            win32clipboard.CloseClipboard()
            return {"status": "ok", "text": text}
        except ImportError:
            return {"status": "error", "error": "pywin32 not installed"}

    def screenshot(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            import io
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            artifact = artifact_manager.save_file(
                name=params.get("name", "desktop_screenshot"),
                content=buf.getvalue(),
                automation_id=ctx.automation_id,
                extension="png",
            )
            return {"status": "ok", "artifact_id": artifact.id, "path": artifact.path}
        except ImportError:
            return {"status": "error", "error": "Pillow not installed"}

    def set_volume(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        level = params.get("level", 50)
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
            return {"status": "ok", "level": level}
        except ImportError:
            return {"status": "error", "error": "pycaw not installed"}

    def open_explorer(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        path = params.get("path", "")
        os.startfile(path)
        return {"status": "ok", "path": path}

    def lock_screen(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], timeout=10)
        return {"status": "ok"}

    def get_installed_apps(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | "
             "Select-Object DisplayName | Where-Object {$_.DisplayName -ne $null} | "
             "Sort-Object DisplayName | ConvertTo-Json"],
            capture_output=True, text=True, timeout=30,
        )
        import json
        try:
            apps = json.loads(result.stdout)
            if isinstance(apps, dict):
                apps = [apps]
            names = [a.get("DisplayName", "") for a in apps]
            return {"status": "ok", "count": len(names), "apps": names[:50]}
        except Exception:
            return {"status": "ok", "count": 0, "apps": []}


windows_automation = WindowsAutomation()
