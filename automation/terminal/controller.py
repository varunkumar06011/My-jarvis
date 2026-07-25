import os
import subprocess
import threading
import time
from typing import Any, Optional

from automation.engine.context import AutomationContext
from automation.engine.rollback import RollbackManager
from automation.engine.artifacts import artifact_manager


class TerminalEngine:
    """Terminal/shell automation with streaming, timeout, and cancellation."""

    SHELLS = {
        "powershell": ["powershell", "-NoProfile", "-Command"],
        "cmd": ["cmd", "/C"],
        "wsl": ["wsl", "--"],
        "bash": ["bash", "-c"],
    }

    def execute(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        command = params.get("command", "")
        shell = params.get("shell", "powershell")
        timeout = params.get("timeout", 60)
        cwd = params.get("cwd", "")
        env = params.get("env", {})

        shell_cmd = self.SHELLS.get(shell, self.SHELLS["powershell"])
        full_cmd = shell_cmd + [command]

        env_vars = dict(os.environ)
        env_vars.update(env)

        try:
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd or None,
                env=env_vars,
            )
            return {
                "status": "ok" if result.returncode == 0 else "error",
                "exit_code": result.returncode,
                "stdout": result.stdout[:5000],
                "stderr": result.stderr[:5000],
                "shell": shell,
                "command": command,
            }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "command": command, "timeout": timeout}
        except Exception as e:
            return {"status": "error", "error": str(e), "command": command}

    def safe_execute(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        """Execute with a whitelist of allowed commands."""
        command = params.get("command", "")
        allowed_patterns = params.get("allowed", [
            "dir", "ls", "echo", "type", "cat", "Get-Process",
            "Get-Service", "ipconfig", "systeminfo", "whoami",
            "python --version", "git status", "git log",
        ])

        is_allowed = any(command.strip().startswith(p) for p in allowed_patterns)
        if not is_allowed:
            return {"status": "blocked", "command": command, "reason": "Command not in safe list"}

        return self.execute(params, ctx, rollback)

    def stream_execute(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        """Execute and capture output line by line."""
        command = params.get("command", "")
        shell = params.get("shell", "powershell")
        timeout = params.get("timeout", 60)

        shell_cmd = self.SHELLS.get(shell, self.SHELLS["powershell"])
        full_cmd = shell_cmd + [command]

        try:
            proc = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout_lines = []
            try:
                for line in proc.stdout:
                    stdout_lines.append(line.rstrip())
                    if len(stdout_lines) >= 100:
                        break
            except Exception:
                pass
            proc.wait(timeout=timeout)

            return {
                "status": "ok" if proc.returncode == 0 else "error",
                "exit_code": proc.returncode,
                "stdout": "\n".join(stdout_lines),
                "lines": len(stdout_lines),
                "shell": shell,
                "command": command,
            }
        except subprocess.TimeoutExpired:
            proc.kill()
            return {"status": "timeout", "command": command}
        except Exception as e:
            return {"status": "error", "error": str(e)}


terminal_engine = TerminalEngine()
