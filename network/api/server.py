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
from network.api.errors import ErrorCode
from network.api.middleware import AuditMiddleware, RequestIDMiddleware, RequestSizeLimitMiddleware
from network.api.rate_limiter import RateLimitMiddleware
from network.api.schemas import (
    ErrorResponse,
    LoginRequest,
    SuccessResponse,
    TokenResponse,
)
from network.api.config_migration import migrate_config
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
from network.routes.system import router as system_router
from network.routes.diagnostics import router as diagnostics_router
from network.routes.automation import router as automation_router
from network.routes.plugins_api import router as automation_plugins_router
from network.routes.cto import router as cto_router
from network.routes.learning import router as learning_router
from network.routes.sync import router as sync_router
from network.routes.ecosystem import router as ecosystem_router
from network.routes.marketplace import router as marketplace_router
from network.routes.release import router as release_router
from network.routes.projects import router as projects_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    print("[API] Starting Secure Communication Platform...")

    # Run config migration
    migration = migrate_config()
    print(f"[API] Config: {migration['status']} (v{migration.get('version', '?')})")

    # Register services in the Service Registry
    registry.register("api_server", app)
    registry.register("ws_manager", ws_manager)
    registry.register("rate_limiter", __import__("network.api.rate_limiter", fromlist=["rate_limiter"]).rate_limiter)
    registry.register("api_key_manager", api_key_manager)
    registry.register("jwt_manager", jwt_manager)
    registry.register("audit_logger", audit_logger)

    # Observability services
    from core.event_store import event_store, subscribe_event_store_to_bus
    from core.metrics import metrics
    from core.telemetry import telemetry
    from core.recovery import recovery_engine
    from core.structured_log import structured_logger
    from flags import flag_manager

    subscribe_event_store_to_bus()
    metrics.start_collection()
    recovery_engine.start()

    registry.register("event_store", event_store)
    registry.register("metrics", metrics)
    registry.register("telemetry", telemetry)
    registry.register("recovery_engine", recovery_engine)
    registry.register("structured_logger", structured_logger)
    registry.register("flag_manager", flag_manager)

    # Automation platform
    from automation.engine.automation_engine import automation_engine
    from automation.register_actions import register_all_actions
    register_all_actions()
    automation_engine.start()
    registry.register("automation_engine", automation_engine)
    from automation.plugins.base import plugin_loader
    registry.register("plugin_loader", plugin_loader)

    # AI Engineering Ecosystem (Steps 30-34)
    if flag_manager.is_enabled("repo_intelligence"):
        from ai.repo.intelligence import repo_intelligence
        registry.register("repo_intelligence", repo_intelligence)
        print("[API] ✅ Repository Intelligence Platform loaded")

    if flag_manager.is_enabled("knowledge_engine"):
        from ai.knowledge.engine import knowledge_engine
        knowledge_indexer_loaded = knowledge_engine.indexer.load()
        registry.register("knowledge_engine", knowledge_engine)
        print("[API] ✅ Enterprise Knowledge Engine (RAG) loaded")

    if flag_manager.is_enabled("ai_engineer"):
        from ai.engineer.engineer import ai_engineer
        registry.register("ai_engineer", ai_engineer)
        print("[API] ✅ AI Software Engineer loaded")

    if flag_manager.is_enabled("engineering_agents"):
        from ai.agents.coordinator import agent_coordinator
        registry.register("agent_coordinator", agent_coordinator)
        print(f"[API] ✅ Engineering Agents loaded ({len(agent_coordinator.agents)} agents)")

    if flag_manager.is_enabled("dev_ecosystem"):
        from ai.ecosystem.ecosystem import dev_ecosystem
        registry.register("dev_ecosystem", dev_ecosystem)
        print("[API] ✅ Development Ecosystem loaded")

    # Bridge EventBus → WebSocket
    subscribe_to_event_bus()

    bus.publish("ApplicationStarted", {"component": "api_server", "services": registry.list_services()})

    print(f"[API] ✅ Server running at http://{API_HOST}:{API_PORT}")
    print(f"[API] ✅ Docs at http://{API_HOST}:{API_PORT}/docs")
    print(f"[API] ✅ WebSocket at ws://{API_HOST}:{API_PORT}/ws")

    yield

    # ── Shutdown ──
    print("[API] Shutting down...")
    metrics.stop_collection()
    recovery_engine.stop()
    automation_engine.stop()
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

    # ── Middleware (order matters: outermost runs first) ──
    app.add_middleware(GZipMiddleware, minimum_size=512)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)
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
    app.include_router(system_router)
    app.include_router(diagnostics_router)
    app.include_router(automation_router)
    app.include_router(automation_plugins_router)
    app.include_router(cto_router)
    app.include_router(learning_router)
    app.include_router(sync_router)
    app.include_router(marketplace_router)
    app.include_router(release_router)
    app.include_router(ecosystem_router)
    app.include_router(projects_router)

    # ── Backward-compat redirects (/api/* -> /api/v1/*) ──
    from fastapi.responses import RedirectResponse

    _v1_paths = [
        "/chat", "/chat/stream", "/voice", "/tool", "/repo-query",
        "/status", "/health", "/plugins", "/plugins/reload",
        "/memory", "/memory/sessions", "/settings",
    ]

    for p in _v1_paths:
        def make_redirect(old_path=p):
            async def redirect():
                return RedirectResponse(url=f"/api/v1{old_path}", status_code=308)
            return redirect

        methods = ["GET", "POST", "DELETE"]
        for method in methods:
            app.add_api_route(f"/api{p}", make_redirect(), methods=[method], include_in_schema=False)

    # ── Root ──
    @app.get("/", response_model=SuccessResponse)
    async def root():
        return SuccessResponse(status="ok", message=f"{APP_NAME} API v{VERSION}")

    # ── Web Client ──
    @app.get("/web", include_in_schema=False)
    async def web_client():
        from fastapi.responses import HTMLResponse
        from pathlib import Path
        web_file = Path(__file__).parent.parent.parent / "desktop" / "web_client.html"
        if web_file.exists():
            return HTMLResponse(web_file.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>Web client not found</h1>", status_code=404)

    # ── Auth: Login (JWT) ──
    @app.post("/api/v1/auth/login", response_model=TokenResponse, tags=["auth"])
    @app.post("/api/auth/login", response_model=TokenResponse, tags=["auth"], include_in_schema=False)
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
    @app.post("/api/v1/auth/refresh", response_model=TokenResponse, tags=["auth"])
    @app.post("/api/auth/refresh", response_model=TokenResponse, tags=["auth"], include_in_schema=False)
    async def refresh_token(token: str = Query(...)):
        new_token = jwt_manager.refresh_token(token)
        if new_token is None:
            return JSONResponse(status_code=401, content={"error": "Invalid or expired token"})
        return TokenResponse(access_token=new_token, expires_in=3600)

    # ── WebSocket (with JWT + API key auth) ──
    @app.websocket("/ws")
    async def websocket_endpoint(
        websocket: WebSocket,
        api_key: Optional[str] = Query(default=None),
        token: Optional[str] = Query(default=None),
        subscriptions: Optional[str] = Query(default=None),
    ):
        auth_ok = False
        client_name = "ws-client"
        permissions = []

        # Try API key first
        if api_key and (api_key_manager.validate(api_key) or api_key == API_DEFAULT_KEY):
            auth_ok = True
            client_name = api_key_manager.get_name(api_key) or "ws-client"
            permissions = api_key_manager.get_permissions(api_key)
            if api_key == API_DEFAULT_KEY:
                permissions = ["read", "chat", "voice", "execute_tools", "settings", "plugins", "admin"]

        # Try JWT token
        if not auth_ok and token:
            payload = jwt_manager.verify_token(token)
            if payload is not None:
                auth_ok = True
                client_name = payload.get("sub", "ws-client")
                permissions = payload.get("permissions", [])

        if not auth_ok:
            await websocket.close(code=4001, reason="Authentication failed")
            audit_logger.auth_failed("ws")
            return

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

    # ── Unified exception handlers ──
    from fastapi.exceptions import RequestValidationError

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        request_id = request.headers.get("X-Request-ID", "-")
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation error",
                "code": ErrorCode.VALIDATION_ERROR.value,
                "detail": exc.errors(),
                "request_id": request_id,
            },
        )

    @app.exception_handler(500)
    async def internal_error(request, exc):
        request_id = request.headers.get("X-Request-ID", "-")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "code": ErrorCode.INTERNAL_ERROR.value,
                "detail": str(exc),
                "request_id": request_id,
            },
        )

    @app.exception_handler(404)
    async def not_found(request, exc):
        request_id = request.headers.get("X-Request-ID", "-")
        return JSONResponse(
            status_code=404,
            content={
                "error": "Resource not found",
                "code": ErrorCode.RESOURCE_NOT_FOUND.value,
                "request_id": request_id,
            },
        )

    return app


app = create_app()


def run_server(host: str = API_HOST, port: int = API_PORT):
    """Run the API server (blocking). Call from a thread."""
    uvicorn.run(app, host=host, port=port, log_level="info")


def _kill_process_on_port(port: int):
    try:
        import subprocess
        result = subprocess.run(
            ["netstat", "-ano", "-p", "TCP", "-a"],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.strip().split()
                pid = parts[-1]
                if pid.isdigit() and int(pid) != 0:
                    subprocess.run(["taskkill", "/F", "/PID", pid],
                                   capture_output=True, timeout=10)
                    print(f"[API] Killed stale process {pid} on port {port}")
                    time.sleep(1)
    except Exception:
        pass


def start_server_in_thread(host: str = API_HOST, port: int = API_PORT) -> threading.Thread:
    """Start the API server in a daemon thread."""
    _kill_process_on_port(port)

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    def _run():
        try:
            server.run()
        except OSError as e:
            if "10048" in str(e) or "already in use" in str(e).lower():
                print(f"[API] ⚠ Port {port} still in use, skipping API server")
            else:
                raise

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    run_server()
