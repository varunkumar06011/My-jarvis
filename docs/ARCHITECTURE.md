# Jarvis OS v1 — Architecture Documentation

## Overview

Jarvis is an offline-first AI assistant platform with voice, chat, automation,
AI engineering, and executive intelligence capabilities.

## Core Architecture

### Event-Driven Design
- **Event Bus** (`core/event_bus.py`) — Pub/sub communication between all components
- **Event Store** (`core/event_store.py`) — Persistent event log with search, replay, and statistics
- **Correlation** (`core/correlation.py`) — Request/automation correlation IDs

### Service Management
- **Service Registry** (`core/service_registry.py`) — Dependency injection container
- **Health Manager** (`core/health_manager.py`) — Continuous health monitoring
- **Recovery Engine** (`core/recovery.py`) — Automatic recovery with retry/cooldown/escalation
- **Task Queue** (`core/task_queue.py`) — Priority-based background task execution

### Observability
- **Metrics** (`core/metrics.py`) — Counters, gauges, histograms, timers
- **Telemetry** (`core/telemetry.py`) — Local-only telemetry with crash reporting
- **Structured Logging** (`core/structured_log.py`) — JSON structured logs

### Feature Management
- **Feature Flags** (`flags/__init__.py`) — Runtime feature toggles with persistence

## Application Layer

### Entry Points
- **Production** (`app/bootstrap.py`) — Full production startup with GUI, tray, API
- **Development** (`main.py`) — CLI development mode

### Lifecycle
- **Lifecycle Manager** (`app/lifecycle.py`) — State machine: STARTING → READY → LISTENING → PROCESSING → SPEAKING → IDLE → SHUTDOWN
- **Startup Validation** (`app/startup.py`) — Directory, dependency, and model checks
- **System Tray** (`app/tray.py`) — Background tray icon with lifecycle controls
- **Settings** (`app/settings.py`) — Windows auto-start management

## Desktop GUI (PySide6)

### Pages
- **Home** — Dashboard with lifecycle, CPU, memory, plugins, uptime
- **Chat** — Conversation interface with background LLM calls
- **Automation** — Workflow monitoring and control
- **Performance** — System metrics, latency, event stats, feature flags
- **AI CTO** — Executive dashboard with health, security, reports, architecture analysis
- **Learning** — Pattern library, decision history, user preferences
- **Settings** — Voice config, auto-start, model selection
- **Plugins** — Installed plugin management
- **Marketplace** — Plugin discovery, installation, updates
- **Diagnostics** — Services, health checks, event log
- **Logs** — Structured log viewer with filtering
- **Models** — AI model information
- **About** — Architecture summary

### Threading Rules
- UI thread never performs LLM inference, STT, TTS, or automation
- All heavy work uses QThread or Task Queue
- UI receives updates through Event Bus subscriptions

## Voice Pipeline
- **Wake Word** (`voice/wake_word.py`) — OpenWakeWord (ONNX)
- **STT** (`voice/stt.py`) — OpenAI Whisper + Silero VAD
- **TTS** (`voice/tts.py`) — Piper (offline neural TTS)

## AI Brain
- **LLM** (`brain/llm.py`) — Ollama with retry, stale process cleanup, CPU-only inference
- **Router** (`core/router.py`) — AI-powered tool routing

## Automation Platform
- **Engine** (`automation/engine/`) — Workflow execution, queue, scheduler, approvals
- **Plugins** (`automation/plugins/`) — Dev, browser, filesystem, terminal, docker, office, database, printer
- **Policies** (`automation/policies/`) — Risk levels, approval requirements
- **Rollback** (`automation/engine/rollback.py`) — Automatic rollback on failure

## API Server (FastAPI)
- **Versioned API** — All endpoints under `/api/v1/`
- **Authentication** — API keys + JWT tokens
- **WebSocket** — Real-time event streaming
- **Rate Limiting** — Per-minute and per-hour limits
- **Audit Logging** — All requests logged
- **Security** — Encryption, permissions, API key management

## AI CTO Platform
- **Executive Dashboard** (`ai/cto/dashboard.py`) — Project health, system status, service health
- **Reports** (`ai/cto/reports.py`) — Daily, weekly, monthly report generation
- **Architecture Analysis** (`ai/cto/architecture.py`) — AST-based code analysis for bottlenecks, coupling, complexity

## Learning & Improvement
- **Pattern Library** (`ai/learning/patterns.py`) — Reusable solutions with success tracking
- **Decision History** (`ai/learning/decisions.py`) — Architecture decision records
- **User Preferences** (`ai/learning/preferences.py`) — Coding style, naming, workflows, common fixes

## Multi-Device Ecosystem
- **Sync Manager** (`sync/manager.py`) — Device registration, heartbeat, push/pull sync
- **Web Client** (`desktop/web_client.html`) — Browser-based chat interface

## Plugin Marketplace
- **Registry** (`marketplace/registry.py`) — Discovery, installation, updates, versioning
- **Categories** — Development, Browser, Office, AI, Business, Restaurant/POS, Monitoring
- **Security** — Digital signatures, permissions, dependency validation

## Release Engineering
- **Release Manager** (`marketplace/release.py`) — Build, installer scripts, backup/restore, tests

## Directory Structure
```
jarvis/
├── ai/              # AI CTO + Learning
├── app/             # Application layer (bootstrap, lifecycle, tray)
├── assets/          # Piper TTS, models
├── automation/      # Automation platform
├── brain/           # LLM
├── configs/         # Configuration
├── core/            # Core infrastructure
├── data/            # Runtime data
├── desktop/         # PySide6 GUI
├── flags/           # Feature flags
├── logs/            # Log files
├── marketplace/     # Plugin marketplace + release
├── memory/          # Conversation history
├── network/         # FastAPI server
├── plugins/         # Tool plugins
├── services/        # Assistant service
├── sync/            # Multi-device sync
├── tests/           # Test suite
└── voice/           # Wake word, STT, TTS
```
