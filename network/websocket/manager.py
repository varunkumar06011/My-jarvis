import asyncio
import json
import time
from typing import Any, Optional

from fastapi import WebSocket

from network.security.audit import audit_logger
from network.websocket.events import WSEventType


class ConnectionInfo:
    def __init__(self, websocket: WebSocket, client_id: str, subscriptions: list[str] | None = None):
        self.websocket = websocket
        self.client_id = client_id
        self.subscriptions = subscriptions or []
        self.connected_at = time.time()
        self._send_lock = asyncio.Lock()

    async def send(self, event: str, data: Any = None):
        message = json.dumps({"event": event, "data": data, "timestamp": time.time()})
        async with self._send_lock:
            try:
                await self.websocket.send_text(message)
            except Exception:
                pass

    def is_subscribed(self, event: str) -> bool:
        if not self.subscriptions:
            return True  # subscribe to all if no filter
        return event in self.subscriptions


class WebSocketManager:
    def __init__(self):
        self._connections: dict[str, ConnectionInfo] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str, subscriptions: list[str] | None = None):
        await websocket.accept()
        conn = ConnectionInfo(websocket, client_id, subscriptions)
        async with self._lock:
            self._connections[client_id] = conn
        audit_logger.ws_connected(client_id)
        await conn.send("Connected", {"client_id": client_id})

    async def disconnect(self, client_id: str):
        async with self._lock:
            self._connections.pop(client_id, None)
        audit_logger.ws_disconnected(client_id)

    async def broadcast(self, event: str, data: Any = None):
        async with self._lock:
            connections = list(self._connections.values())

        for conn in connections:
            if conn.is_subscribed(event):
                await conn.send(event, data)

    async def send_to(self, client_id: str, event: str, data: Any = None):
        conn = self._connections.get(client_id)
        if conn:
            await conn.send(event, data)

    def get_connection_count(self) -> int:
        return len(self._connections)

    def get_connected_clients(self) -> list[str]:
        return list(self._connections.keys())


ws_manager = WebSocketManager()


def subscribe_to_event_bus():
    """Bridge EventBus events to WebSocket clients."""
    from core.event_bus import bus
    from network.websocket.events import WSEventType

    def make_handler(event_name: str):
        def handler(data):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(ws_manager.broadcast(event_name, data), loop=loop)
            except RuntimeError:
                # No running loop — skip (server not started yet)
                pass

        return handler

    for event_type in WSEventType:
        bus.subscribe(event_type.value, make_handler(event_type.value))
