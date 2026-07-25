import json
import threading
from typing import Any, Optional

import requests
import websocket


class JarvisSDK:
    """Python SDK client for the Jarvis Secure Communication Platform."""

    def __init__(self, base_url: str = "http://localhost:8100", api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._token: Optional[str] = None
        self._ws: Optional[websocket.WebSocketApp] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._api_base = f"{self.base_url}/api/v1"

    @property
    def _headers(self) -> dict:
        token = self._token or self.api_key
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    # ── Auth ──

    def login(self) -> dict:
        resp = requests.post(
            f"{self._api_base}/auth/login",
            json={"api_key": self.api_key},
        )
        data = resp.json()
        if resp.status_code == 200:
            self._token = data["access_token"]
        return data

    def refresh_token(self) -> dict:
        if not self._token:
            raise RuntimeError("No token to refresh. Call login() first.")
        resp = requests.post(
            f"{self._api_base}/auth/refresh",
            params={"token": self._token},
        )
        data = resp.json()
        if resp.status_code == 200:
            self._token = data["access_token"]
        return data

    # ── Chat ──

    def chat(self, message: str, session: str = "default") -> dict:
        resp = requests.post(
            f"{self._api_base}/chat",
            json={"message": message, "session": session},
            headers=self._headers,
        )
        return resp.json()

    def chat_stream(self, message: str, session: str = "default"):
        resp = requests.post(
            f"{self._api_base}/chat/stream",
            json={"message": message, "session": session},
            headers=self._headers,
            stream=True,
        )
        for line in resp.iter_lines():
            if line:
                yield json.loads(line.decode("utf-8"))

    # ── Voice ──

    def speak(self, text: str) -> dict:
        resp = requests.post(
            f"{self._api_base}/voice",
            json={"text": text},
            headers=self._headers,
        )
        return resp.json()

    # ── Tools ──

    def execute_tool(self, tool: str, input_data: str = None) -> dict:
        payload = {"tool": tool}
        if input_data:
            payload["input"] = input_data
        resp = requests.post(
            f"{self._api_base}/tool",
            json=payload,
            headers=self._headers,
        )
        return resp.json()

    # ── Status ──

    def status(self) -> dict:
        resp = requests.get(f"{self._api_base}/status", headers=self._headers)
        return resp.json()

    # ── Health ──

    def health(self) -> dict:
        resp = requests.get(f"{self._api_base}/health", headers=self._headers)
        return resp.json()

    # ── Plugins ──

    def list_plugins(self) -> dict:
        resp = requests.get(f"{self._api_base}/plugins", headers=self._headers)
        return resp.json()

    def reload_plugins(self) -> dict:
        resp = requests.post(f"{self._api_base}/plugins/reload", headers=self._headers)
        return resp.json()

    # ── Memory ──

    def get_memory(self, session: str = "default") -> dict:
        resp = requests.get(
            f"{self._api_base}/memory",
            params={"session": session},
            headers=self._headers,
        )
        return resp.json()

    def list_sessions(self) -> list:
        resp = requests.get(f"{self._api_base}/memory/sessions", headers=self._headers)
        return resp.json()

    # ── Settings ──

    def get_settings(self) -> dict:
        resp = requests.get(f"{self._api_base}/settings", headers=self._headers)
        return resp.json()

    def update_settings(self, **kwargs) -> dict:
        payload = {k: v for k, v in kwargs.items() if v is not None}
        resp = requests.post(
            f"{self._api_base}/settings",
            json=payload,
            headers=self._headers,
        )
        return resp.json()

    # ── System ──

    def restart(self) -> dict:
        resp = requests.post(f"{self._api_base}/restart", headers=self._headers)
        return resp.json()

    def create_backup(self) -> dict:
        resp = requests.post(f"{self._api_base}/backup", headers=self._headers)
        return resp.json()

    def list_backups(self) -> list:
        resp = requests.get(f"{self._api_base}/backups", headers=self._headers)
        return resp.json()

    def restore_backup(self, backup_id: str) -> dict:
        resp = requests.post(f"{self._api_base}/backup/restore/{backup_id}", headers=self._headers)
        return resp.json()

    def delete_backup(self, backup_id: str) -> dict:
        resp = requests.delete(f"{self._api_base}/backup/{backup_id}", headers=self._headers)
        return resp.json()

    # ── Diagnostics ──

    def metrics(self) -> dict:
        resp = requests.get(f"{self._api_base}/metrics", headers=self._headers)
        return resp.json()

    def performance(self) -> dict:
        resp = requests.get(f"{self._api_base}/performance", headers=self._headers)
        return resp.json()

    def timeline(self, limit: int = 50) -> list:
        resp = requests.get(f"{self._api_base}/timeline", params={"limit": limit}, headers=self._headers)
        return resp.json()

    def events(self, **filters) -> list:
        resp = requests.get(f"{self._api_base}/events", params=filters, headers=self._headers)
        return resp.json()

    def event_stats(self) -> dict:
        resp = requests.get(f"{self._api_base}/events/stats", headers=self._headers)
        return resp.json()

    def export_events(self) -> dict:
        resp = requests.get(f"{self._api_base}/events/export", headers=self._headers)
        return resp.json()

    def telemetry(self, level: str = None, category: str = None, limit: int = 100) -> list:
        params = {"limit": limit}
        if level:
            params["level"] = level
        if category:
            params["category"] = category
        resp = requests.get(f"{self._api_base}/telemetry", params=params, headers=self._headers)
        return resp.json()

    def telemetry_summary(self) -> dict:
        resp = requests.get(f"{self._api_base}/telemetry/summary", headers=self._headers)
        return resp.json()

    def logs(self, level: str = None, category: str = None, limit: int = 100) -> list:
        params = {"limit": limit}
        if level:
            params["level"] = level
        if category:
            params["category"] = category
        resp = requests.get(f"{self._api_base}/logs", params=params, headers=self._headers)
        return resp.json()

    def logs_summary(self) -> dict:
        resp = requests.get(f"{self._api_base}/logs/summary", headers=self._headers)
        return resp.json()

    def recovery_info(self) -> dict:
        resp = requests.get(f"{self._api_base}/recovery", headers=self._headers)
        return resp.json()

    def feature_flags(self) -> dict:
        resp = requests.get(f"{self._api_base}/flags", headers=self._headers)
        return resp.json()

    def set_feature_flag(self, name: str, enabled: bool) -> dict:
        resp = requests.post(f"{self._api_base}/flags/{name}", params={"enabled": enabled}, headers=self._headers)
        return resp.json()

    # ── Automation ──

    def start_automation(self, workflow_id: str, variables: dict = None, sync: bool = False, priority: int = 5) -> dict:
        resp = requests.post(f"{self._api_base}/automation/start", json={"workflow_id": workflow_id, "variables": variables, "sync": sync, "priority": priority}, headers=self._headers)
        return resp.json()

    def pause_automation(self, automation_id: str) -> dict:
        resp = requests.post(f"{self._api_base}/automation/{automation_id}/pause", headers=self._headers)
        return resp.json()

    def resume_automation(self, automation_id: str) -> dict:
        resp = requests.post(f"{self._api_base}/automation/{automation_id}/resume", headers=self._headers)
        return resp.json()

    def cancel_automation(self, automation_id: str) -> dict:
        resp = requests.post(f"{self._api_base}/automation/{automation_id}/cancel", headers=self._headers)
        return resp.json()

    def rollback_automation(self, automation_id: str) -> dict:
        resp = requests.post(f"{self._api_base}/automation/{automation_id}/rollback", headers=self._headers)
        return resp.json()

    def automation_status(self, automation_id: str) -> dict:
        resp = requests.get(f"{self._api_base}/automation/{automation_id}/status", headers=self._headers)
        return resp.json()

    def automation_history(self, limit: int = 50, status: str = None) -> list:
        params = {"limit": limit}
        if status:
            params["status"] = status
        resp = requests.get(f"{self._api_base}/automation/history", params=params, headers=self._headers)
        return resp.json()

    def automation_workflows(self) -> list:
        resp = requests.get(f"{self._api_base}/automation/workflows", headers=self._headers)
        return resp.json()

    def create_workflow(self, workflow: dict) -> dict:
        resp = requests.post(f"{self._api_base}/automation/workflows", json={"workflow": workflow}, headers=self._headers)
        return resp.json()

    def automation_templates(self) -> list:
        resp = requests.get(f"{self._api_base}/automation/templates", headers=self._headers)
        return resp.json()

    def validate_workflow(self, workflow: dict) -> dict:
        resp = requests.post(f"{self._api_base}/automation/validate", json={"workflow": workflow}, headers=self._headers)
        return resp.json()

    def automation_queue(self) -> dict:
        resp = requests.get(f"{self._api_base}/automation/queue", headers=self._headers)
        return resp.json()

    def automation_approvals(self) -> list:
        resp = requests.get(f"{self._api_base}/automation/approvals", headers=self._headers)
        return resp.json()

    def approve_request(self, approval_id: str) -> dict:
        resp = requests.post(f"{self._api_base}/automation/approvals/{approval_id}/approve", headers=self._headers)
        return resp.json()

    def reject_request(self, approval_id: str) -> dict:
        resp = requests.post(f"{self._api_base}/automation/approvals/{approval_id}/reject", headers=self._headers)
        return resp.json()

    def schedule_automation(self, name: str, workflow_id: str, schedule_type: str = "one_time", interval: float = 0, delay: float = 0, variables: dict = None) -> dict:
        resp = requests.post(f"{self._api_base}/automation/schedule", json={"name": name, "workflow_id": workflow_id, "schedule_type": schedule_type, "interval": interval, "delay": delay, "variables": variables}, headers=self._headers)
        return resp.json()

    # ── Plugins ──

    def list_plugins(self) -> list:
        resp = requests.get(f"{self._api_base}/automation/plugins", headers=self._headers)
        return resp.json()

    def get_plugin(self, plugin_name: str) -> dict:
        resp = requests.get(f"{self._api_base}/automation/plugins/{plugin_name}", headers=self._headers)
        return resp.json()

    def plugin_workflows(self, plugin_name: str) -> dict:
        resp = requests.get(f"{self._api_base}/automation/plugins/{plugin_name}/workflows", headers=self._headers)
        return resp.json()

    def plugin_actions(self, plugin_name: str) -> dict:
        resp = requests.get(f"{self._api_base}/automation/plugins/{plugin_name}/actions", headers=self._headers)
        return resp.json()

    def reload_plugins(self) -> dict:
        resp = requests.post(f"{self._api_base}/automation/plugins/reload", headers=self._headers)
        return resp.json()

    # ── WebSocket ──

    def connect_ws(
        self,
        on_event=None,
        subscriptions: list[str] | None = None,
        use_jwt: bool = False,
    ):
        ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        if use_jwt and self._token:
            ws_url += f"/ws?token={self._token}"
        else:
            ws_url += f"/ws?api_key={self.api_key}"
        if subscriptions:
            ws_url += f"&subscriptions={','.join(subscriptions)}"

        def on_message(ws, message):
            if on_event:
                try:
                    data = json.loads(message)
                    on_event(data)
                except json.JSONDecodeError:
                    on_event({"raw": message})

        def on_error(ws, error):
            print(f"[SDK] WebSocket error: {error}")

        def on_close(ws, close_status, close_msg):
            print(f"[SDK] WebSocket closed: {close_status} {close_msg}")

        def on_open(ws):
            print("[SDK] WebSocket connected")

        self._ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open,
        )

        self._ws_thread = threading.Thread(
            target=self._ws.run_forever,
            daemon=True,
        )
        self._ws_thread.start()

    def disconnect_ws(self):
        if self._ws:
            self._ws.close()
            self._ws = None
            self._ws_thread = None
