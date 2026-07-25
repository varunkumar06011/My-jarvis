from datetime import datetime
from pathlib import Path
from typing import Any, Optional

AUDIT_LOG = Path("logs/audit.log")


class AuditLogger:
    def __init__(self, log_file: Path = AUDIT_LOG):
        self._log_file = log_file
        self._log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(self, action: str, client: Optional[str] = None, detail: Any = None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {action}"
        if client:
            entry += f" | client={client}"
        if detail:
            entry += f" | detail={detail}"

        with open(self._log_file, "a", encoding="utf-8") as f:
            f.write(entry + "\n")

    def client_connected(self, client: str):
        self.log("ClientConnected", client)

    def client_disconnected(self, client: str):
        self.log("ClientDisconnected", client)

    def tool_executed(self, client: str, tool: str, input_data: str):
        self.log("ToolExecuted", client, f"tool={tool} input={input_data}")

    def auth_failed(self, client: Optional[str] = None):
        self.log("AuthenticationFailed", client)

    def permission_denied(self, client: str, permission: str):
        self.log("PermissionDenied", client, f"permission={permission}")

    def ws_connected(self, client: str):
        self.log("WebSocketConnected", client)

    def ws_disconnected(self, client: str):
        self.log("WebSocketDisconnected", client)


audit_logger = AuditLogger()
