import asyncio
import json
import threading
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from configs.config import (
    API_HOST,
    API_PORT,
    API_DEFAULT_KEY,
    API_ENABLE_DOCS,
    APP_NAME,
    VERSION,
)
from core.event_bus import bus
from core.service_registry import registry
from network.api.middleware import AuditMiddleware, RequestSizeLimitMiddleware
from network.api.rate_limiter import RateLimitMiddleware
from network.api.schemas import (
    ErrorResponse,
    LoginRequest,
    SuccessResponse,
    TokenResponse,
)
from network.security.api_keys import api_key_manager
from network.security.audit import audit_logger
from network.security.jwt import jwt_manager
from network.websocket.events import WSEventType
from network.websocket.manager import ws_manager, subscribe_to_event_bus

# Import routers
from network.routes.chat import router as chat_router
from network.routes.voice import router as voice_router
from network.routes.tools import router as tools_router
from network.routes.status import router as status_router
from network.routes.health import router as health_router
from network.routes.plugins import router as plugins_router
from network.routes.memory import router as memory_router
from network.routes.settings import router as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    print("[API] Starting Secure Communication Platform...")

    # Register services in the Service Registry
    registry.register("api_server", app)
    registry.register("ws_manager", ws_manager)
    registry.register("rate_limiter", __import__("network.api.rate_limiter", fromlist=["rate_limiter"]).rate_limiter)
    registry.register("api_key_manager", api_key_manager)
    registry.register("jwt_manager", jwt_manager)
    registry.register("audit_logger", audit_logger)

    # Bridge EventBus → WebSocket
    subscribe_to_event_bus()

    bus.publish("ApplicationStarted", {"component": "api_server", "services": registry.list_services()})

    print(f"[API] ✅ Server running at http://{API_HOST}:{API_PORT}")
    print(f"[API] ✅ Docs at http://{API_HOST}:{API_PORT}/docs")
    print(f"[API] ✅ WebSocket at ws://{API_HOST}:{API_PORT}/ws")

    yield

    # ── Shutdown ──
    print("[API] Shutting down...")
    bus.publish("ApplicationStopped", {"component": "api_server"})
    print("[API] Stopped.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=f"{APP_NAME} API",
        description="Secure Communication Platform for Jarvis AI Assistant",
        version=VERSION,
        docs_url="/docs" if API_ENABLE_DOCS else None,
        redoc_url="/redoc" if API_ENABLE_DOCS else None,
        lifespan=lifespan,
    )

    # ── Middleware ──
    app.add_middleware(GZipMiddleware, minimum_size=512)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestSizeLimitMiddleware, max_body_size=1024 * 1024)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # ── Routes ──
    app.include_router(chat_router)
    app.include_router(voice_router)
    app.include_router(tools_router)
    app.include_router(status_router)
    app.include_router(health_router)
    app.include_router(plugins_router)
    app.include_router(memory_router)
    app.include_router(settings_router)

    # ── Root ──
    @app.get("/", response_model=SuccessResponse)
    async def root():
        return SuccessResponse(status="ok", message=f"{APP_NAME} API v{VERSION}")

    # ── Auth: Login (JWT) ──
    @app.post("/api/auth/login", response_model=TokenResponse, tags=["auth"])
    async def login(request: LoginRequest):
        if not api_key_manager.validate(request.api_key) and request.api_key != API_DEFAULT_KEY:
            audit_logger.auth_failed()
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid API key"},
            )

        name = api_key_manager.get_name(request.api_key) or "jwt-user"
        permissions = api_key_manager.get_permissions(request.api_key)
        if request.api_key == API_DEFAULT_KEY:
            permissions = ["read", "chat", "voice", "execute_tools", "settings", "plugins", "admin"]

        token = jwt_manager.create_token(name, permissions)
        return TokenResponse(access_token=token, expires_in=3600)

    # ── Auth: Refresh ──
    @app.post("/api/auth/refresh", response_model=TokenResponse, tags=["auth"])
    async def refresh_token(token: str = Query(...)):
        new_token = jwt_manager.refresh_token(token)
        if new_token is None:
            return JSONResponse(status_code=401, content={"error": "Invalid or expired token"})
        return TokenResponse(access_token=new_token, expires_in=3600)

    # ── WebSocket ──
    @app.websocket("/ws")
    async def websocket_endpoint(
        websocket: WebSocket,
        api_key: Optional[str] = Query(default=None),
        subscriptions: Optional[str] = Query(default=None),
    ):
        if not api_key or (not api_key_manager.validate(api_key) and api_key != API_DEFAULT_KEY):
            await websocket.close(code=4001, reason="Authentication failed")
            audit_logger.auth_failed("ws")
            return

        client_name = api_key_manager.get_name(api_key) or "ws-client"
        client_id = f"{client_name}-{uuid.uuid4().hex[:8]}"

        sub_list = subscriptions.split(",") if subscriptions else None

        await ws_manager.connect(websocket, client_id, sub_list)

        try:
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                    event = msg.get("event", "")

                    if event == "ping":
                        await ws_manager.send_to(client_id, "pong", {"timestamp": time.time()})
                    elif event == "subscribe":
                        new_subs = msg.get("data", [])
                        conn = ws_manager._connections.get(client_id)
                        if conn:
                            conn.subscriptions = new_subs
                            await ws_manager.send_to(client_id, "Subscribed", {"events": new_subs})

                except json.JSONDecodeError:
                    await ws_manager.send_to(client_id, "Error", {"message": "Invalid JSON"})
        except WebSocketDisconnect:
            await ws_manager.disconnect(client_id)
        except Exception as e:
            audit_logger.log("WebSocketError", client_id, str(e))
            await ws_manager.disconnect(client_id)

    # ── Exception handlers ──
    @app.exception_handler(500)
    async def internal_error(request, exc):
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)},
        )

    return app


app = create_app()


def run_server(host: str = API_HOST, port: int = API_PORT):
    """Run the API server (blocking). Call from a thread."""
    uvicorn.run(app, host=host, port=port, log_level="info")


def start_server_in_thread(host: str = API_HOST, port: int = API_PORT) -> threading.Thread:
    """Start the API server in a daemon thread."""
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    run_server()
