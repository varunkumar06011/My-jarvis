from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Chat ──────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    session: Optional[str] = Field(default="default")


class ChatResponse(BaseModel):
    response: str
    session: str


class ChatStreamChunk(BaseModel):
    token: str
    done: bool = False


# ── Voice ─────────────────────────────────────────────────────────────────

class VoiceRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


class VoiceResponse(BaseModel):
    status: str
    text: str


# ── Tools ─────────────────────────────────────────────────────────────────

class ToolRequest(BaseModel):
    tool: str = Field(..., min_length=1)
    input: Optional[str] = Field(default=None)


class ToolResponse(BaseModel):
    tool: str
    result: str
    error: Optional[str] = None


# ── Status ────────────────────────────────────────────────────────────────

class StatusResponse(BaseModel):
    lifecycle: str
    model: str
    wake_word: str
    plugin_count: int
    queue_size: int
    cpu_percent: float
    ram_percent: float
    version: str


# ── Health ────────────────────────────────────────────────────────────────

class HealthStatus(str, Enum):
    HEALTHY = "Healthy"
    DEGRADED = "Degraded"
    UNAVAILABLE = "Unavailable"


class HealthResponse(BaseModel):
    status: HealthStatus
    services: dict[str, bool] = {}


# ── Plugins ───────────────────────────────────────────────────────────────

class PluginInfo(BaseModel):
    name: str
    description: str


class PluginsResponse(BaseModel):
    plugins: list[PluginInfo]
    count: int


class PluginReloadResponse(BaseModel):
    status: str
    count: int
    plugins: list[str]


# ── Memory ────────────────────────────────────────────────────────────────

class MemoryEntry(BaseModel):
    role: str
    content: str


class MemoryResponse(BaseModel):
    session: str
    entries: list[MemoryEntry]
    count: int


# ── Settings ──────────────────────────────────────────────────────────────

class SettingsResponse(BaseModel):
    model_name: str
    gpu_layers: int
    whisper_model: str
    sample_rate: int
    wake_word: str
    wake_threshold: float
    version: str


class SettingsUpdate(BaseModel):
    model_name: Optional[str] = None
    gpu_layers: Optional[int] = None
    whisper_model: Optional[str] = None
    wake_word: Optional[str] = None
    wake_threshold: Optional[float] = None


class SettingsUpdateResponse(BaseModel):
    status: str
    updated: list[str]


# ── WebSocket ─────────────────────────────────────────────────────────────

class WSEvent(BaseModel):
    event: str
    data: Any = None


class WSAuth(BaseModel):
    api_key: str


# ── Auth ──────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    api_key: str


# ── Generic ───────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


class SuccessResponse(BaseModel):
    status: str
    message: Optional[str] = None
