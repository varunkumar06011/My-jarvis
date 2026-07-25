# Step 27 — Secure Communication Platform (API + WebSocket)

## Goal

Turn Jarvis into a **local AI server** that other applications (desktop, Android, web) can securely communicate with.

## Directory Structure

```text
network/
├── api/
│   ├── server.py          # FastAPI app, lifespan, WebSocket endpoint
│   ├── middleware.py       # Audit + request size limit middleware
│   ├── authentication.py   # Bearer auth (API key + JWT)
│   ├── rate_limiter.py     # Per-client rate limiting (30/min, 100/hour)
│   ├── encryption.py       # Fernet encryption manager
│   └── schemas.py          # Pydantic models for all requests/responses
├── routes/
│   ├── chat.py             # POST /api/chat, POST /api/chat/stream
│   ├── voice.py            # POST /api/voice
│   ├── tools.py            # POST /api/tool
│   ├── status.py           # GET /api/status
│   ├── health.py           # GET /api/health
│   ├── plugins.py          # GET /api/plugins, POST /api/plugins/reload
│   ├── memory.py           # GET /api/memory, GET /api/memory/sessions
│   └── settings.py         # GET /api/settings, POST /api/settings
├── websocket/
│   ├── manager.py          # WebSocket connection manager + EventBus bridge
│   ├── events.py           # WSEventType enum (all event names)
│   └── streaming.py        # Token-by-token streaming helpers
├── security/
│   ├── jwt.py              # HS256 JWT create/verify/refresh
│   ├── api_keys.py         # API key generation, validation, revocation
│   ├── permissions.py      # Permission enum + checker
│   └── audit.py            # Audit logger (connect, disconnect, tool, auth)
└── clients/
    └── sdk.py              # Python SDK client (REST + WebSocket)
```

## Framework

- **FastAPI** — async REST API
- **Uvicorn** — ASGI server
- **Pydantic** — request/response validation
- **WebSockets** — real-time event streaming

## REST Endpoints

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| POST | `/api/chat` | Send message to Jarvis | `chat` |
| POST | `/api/chat/stream` | Stream chat response (NDJSON) | `chat` |
| POST | `/api/voice` | Speak text via TTS | `voice` |
| POST | `/api/tool` | Execute a Jarvis tool | `execute_tools` |
| GET | `/api/status` | Get Jarvis status (lifecycle, CPU, RAM, etc.) | `read` |
| GET | `/api/health` | Get health status (Healthy/Degraded/Unavailable) | `read` |
| GET | `/api/plugins` | List all loaded plugins | `plugins` |
| POST | `/api/plugins/reload` | Reload all plugins | `plugins` |
| GET | `/api/memory` | Get conversation history | `read` |
| GET | `/api/memory/sessions` | List saved sessions | `read` |
| GET | `/api/settings` | Get current configuration | `read` |
| POST | `/api/settings` | Update configuration at runtime | `settings` |
| POST | `/api/auth/login` | Exchange API key for JWT token | — |
| POST | `/api/auth/refresh` | Refresh JWT token | — |

## WebSocket

Connect to `ws://host:port/ws?api_key=YOUR_KEY`

Optional: `&subscriptions=WakeWordDetected,LLMResponse` to filter events.

### Events

- `WakeWordDetected`
- `SpeechStarted`
- `SpeechFinished`
- `LifecycleChanged`
- `TaskStarted`
- `TaskCompleted`
- `TaskFailed`
- `HealthChanged`
- `NotificationCreated`
- `PluginLoaded`
- `LLMResponse`
- `ToolExecuted`

## Security

### Authentication

All endpoints require `Authorization: Bearer API_KEY` header.

Supports:
1. **API Keys** — generated, hashed, stored in `data/api_keys.json`
2. **JWT** — login via `/api/auth/login` to get a token
3. **Dev key** — `jarvis-local-dev-key` (for local development only)

### Permissions

`read`, `chat`, `voice`, `execute_tools`, `settings`, `plugins`, `admin`

### Audit Logging

All security-relevant actions are logged to `logs/audit.log`:
- Client connected/disconnected
- Tool executed
- Authentication failed
- Permission denied
- WebSocket connected/disconnected

## Rate Limiting

- 30 requests/minute per client
- 100 requests/hour per client
- Returns HTTP 429 when exceeded

## Service Registry Integration

Registered during API server lifespan:
- `api_server` — FastAPI app instance
- `ws_manager` — WebSocket manager
- `rate_limiter` — Rate limiter instance
- `api_key_manager` — API key manager
- `jwt_manager` — JWT manager
- `audit_logger` — Audit logger

## Event Bus Integration

The EventBus → WebSocket bridge (`subscribe_to_event_bus()`) subscribes to all `WSEventType` events and broadcasts them to connected WebSocket clients.

Flow: `POST /chat → TaskQueue → LLM → LLMResponse event → WebSocket → Desktop/Android/Web`

## Configuration

In `configs/config.py`:

```python
API_HOST = "0.0.0.0"
API_PORT = 8100
API_DEFAULT_KEY = "jarvis-local-dev-key"
API_RATE_LIMIT_PER_MINUTE = 30
API_RATE_LIMIT_PER_HOUR = 100
API_JWT_SECRET = "jarvis-jwt-secret-change-in-production"
API_JWT_EXPIRE_SECONDS = 3600
API_ENABLE_DOCS = True
```

## SDK Usage

```python
from network.clients.sdk import JarvisSDK

client = JarvisSDK(base_url="http://localhost:8100", api_key="jarvis-local-dev-key")

# Chat
response = client.chat("Hello Jarvis")

# Stream chat
for chunk in client.chat_stream("Tell me a story"):
    print(chunk["token"], end="", flush=True)

# Status
status = client.status()

# WebSocket events
def on_event(data):
    print(f"Event: {data['event']} | Data: {data['data']}")

client.connect_ws(on_event=on_event)
```

## Install Dependencies

```bash
pip install fastapi uvicorn pydantic websockets requests cryptography websocket-client
```

## Success Criteria

- [x] FastAPI server runs alongside Jarvis
- [x] REST endpoints are functional
- [x] WebSocket streams live events
- [x] API key authentication works
- [x] Rate limiting is enforced
- [x] Event Bus is integrated
- [x] Services are registered in the Service Registry
- [x] Audit logs are generated
- [x] API documentation (`/docs`) is available
