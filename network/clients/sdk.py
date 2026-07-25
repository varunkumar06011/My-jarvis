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
            f"{self.base_url}/api/auth/login",
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
            f"{self.base_url}/api/auth/refresh",
            params={"token": self._token},
        )
        data = resp.json()
        if resp.status_code == 200:
            self._token = data["access_token"]
        return data

    # ── Chat ──

    def chat(self, message: str, session: str = "default") -> dict:
        resp = requests.post(
            f"{self.base_url}/api/chat",
            json={"message": message, "session": session},
            headers=self._headers,
        )
        return resp.json()

    def chat_stream(self, message: str, session: str = "default"):
        resp = requests.post(
            f"{self.base_url}/api/chat/stream",
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
            f"{self.base_url}/api/voice",
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
            f"{self.base_url}/api/tool",
            json=payload,
            headers=self._headers,
        )
        return resp.json()

    # ── Status ──

    def status(self) -> dict:
        resp = requests.get(f"{self.base_url}/api/status", headers=self._headers)
        return resp.json()

    # ── Health ──

    def health(self) -> dict:
        resp = requests.get(f"{self.base_url}/api/health", headers=self._headers)
        return resp.json()

    # ── Plugins ──

    def list_plugins(self) -> dict:
        resp = requests.get(f"{self.base_url}/api/plugins", headers=self._headers)
        return resp.json()

    def reload_plugins(self) -> dict:
        resp = requests.post(f"{self.base_url}/api/plugins/reload", headers=self._headers)
        return resp.json()

    # ── Memory ──

    def get_memory(self, session: str = "default") -> dict:
        resp = requests.get(
            f"{self.base_url}/api/memory",
            params={"session": session},
            headers=self._headers,
        )
        return resp.json()

    def list_sessions(self) -> list:
        resp = requests.get(f"{self.base_url}/api/memory/sessions", headers=self._headers)
        return resp.json()

    # ── Settings ──

    def get_settings(self) -> dict:
        resp = requests.get(f"{self.base_url}/api/settings", headers=self._headers)
        return resp.json()

    def update_settings(self, **kwargs) -> dict:
        payload = {k: v for k, v in kwargs.items() if v is not None}
        resp = requests.post(
            f"{self.base_url}/api/settings",
            json=payload,
            headers=self._headers,
        )
        return resp.json()

    # ── WebSocket ──

    def connect_ws(
        self,
        on_event=None,
        subscriptions: list[str] | None = None,
    ):
        ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
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
