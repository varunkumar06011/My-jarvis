# Step 28 — Enterprise Automation Platform

## Goal

Jarvis becomes capable of safely operating the computer like a skilled human operator. This is the reusable execution platform — concrete automation plugins come in Step 29+.

## Architecture

```
automation/
├── engine/
│   ├── automation_engine.py      # Main entry point
│   ├── execution_manager.py       # Orchestrates run/pause/resume/cancel
│   ├── workflow_engine.py         # JSON/YAML/Python workflow parsing
│   ├── state_machine.py           # 10-state lifecycle (nothing bypasses)
│   ├── scheduler.py               # One-time, recurring, delayed jobs
│   ├── queue_manager.py           # Priority queue with workers
│   ├── context.py                 # Correlation IDs + variables
│   ├── confirmations.py           # Approval engine (HIGH/CRITICAL)
│   ├── rollback.py                # Undo tracking for reversible actions
│   ├── artifacts.py               # Output storage (screenshots, PDFs, etc.)
│   ├── history.py                 # Execution records
│   └── variables.py               # Thread-safe variable store
├── browser/controller.py          # Playwright integration
├── windows/controller.py          # Windows OS automation
├── filesystem/controller.py       # File operations with rollback
├── terminal/controller.py         # PowerShell/CMD/WSL/Bash
├── docker/controller.py           # Container/image/compose management
├── database/controller.py         # SQLite/MySQL/PostgreSQL (read-only)
├── printer/controller.py          # Printer queue/job management
├── office/controller.py           # Word/Excel/PPT/PDF
├── recorder/controller.py         # Macro record/replay
├── policies/engine.py             # Risk levels + approval rules
├── validators/workflow_validator.py
├── templates/manager.py           # Reusable workflow templates
├── permissions/__init__.py
└── register_actions.py            # Maps all actions to handlers
```

## State Machine

```
Created → Queued → Running → Completed
                    ↓         ↗
                Paused → Running
                    ↓
                Cancelled

Running → WaitingApproval → Running (approved)
                          → Failed (rejected)

Running → Retrying → Running
         ↓
         Failed

Failed → RolledBack
Completed → RolledBack
```

## Workflow Engine

Supports JSON, YAML, and Python plugin workflows.

Step types: `action`, `condition`, `loop`, `parallel`, `delay`, `approval`, `sub_workflow`, `try_catch`

Features: sequential, parallel, branching, loops, conditions, variables (`{{var}}`), retries, delays, approval gates, sub-workflows, try/catch.

## Policy Engine

38 default policies across 4 risk levels:
- **SAFE**: browser.open, fs.read, docker.ps, etc.
- **MEDIUM**: fs.write, browser.download, printer.print
- **HIGH**: fs.delete, terminal.execute, docker.stop
- **CRITICAL**: windows.power, docker.rm, db.write

HIGH and CRITICAL require approval. MEDIUM+ require rollback metadata.

## Integration Modules

| Module | Actions | Key Features |
|--------|---------|-------------|
| Browser | 11 | Navigate, click, type, screenshot, PDF, download, wait |
| Windows | 10 | Launch/close apps, clipboard, screenshot, volume, explorer |
| Filesystem | 12 | Read, write, copy, move, rename, delete, search, hash, compress |
| Terminal | 3 | Execute, safe_execute (whitelist), stream |
| Docker | 11 | ps, images, logs, restart, stop, start, compose, stats, exec, cleanup |
| Database | 4 | Query (read-only), schema, explain, export CSV |
| Printer | 9 | List, default, jobs, cancel, pause, resume, print, test page |
| Office | 2 | Create (Word/Excel/PPT/PDF), read |
| Macro | 1 | Replay with speed control |

## API Endpoints (27 routes)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/automation/start` | Start workflow (sync or async) |
| POST | `/api/v1/automation/{id}/pause` | Pause execution |
| POST | `/api/v1/automation/{id}/resume` | Resume execution |
| POST | `/api/v1/automation/{id}/cancel` | Cancel execution |
| POST | `/api/v1/automation/{id}/rollback` | Rollback execution |
| GET | `/api/v1/automation/{id}/status` | Get execution status |
| GET | `/api/v1/automation/history` | List execution history |
| GET | `/api/v1/automation/history/summary` | History summary |
| GET | `/api/v1/automation/workflows` | List registered workflows |
| POST | `/api/v1/automation/workflows` | Register new workflow |
| GET | `/api/v1/automation/templates` | List templates |
| GET | `/api/v1/automation/templates/{id}` | Get template detail |
| POST | `/api/v1/automation/templates/{id}/start` | Start from template |
| POST | `/api/v1/automation/validate` | Validate workflow |
| GET | `/api/v1/automation/queue` | Queue status |
| GET | `/api/v1/automation/active` | Active automations |
| GET | `/api/v1/automation/approvals` | Pending approvals |
| POST | `/api/v1/automation/approvals/{id}/approve` | Approve request |
| POST | `/api/v1/automation/approvals/{id}/reject` | Reject request |
| GET | `/api/v1/automation/policies` | List policies |
| GET | `/api/v1/automation/artifacts` | List artifacts |
| POST | `/api/v1/automation/schedule` | Create schedule |
| GET | `/api/v1/automation/schedules` | List schedules |
| DELETE | `/api/v1/automation/schedules/{id}` | Cancel schedule |
| GET | `/api/v1/automation/macros` | List macros |
| POST | `/api/v1/automation/macros/{id}/replay` | Replay macro |
| DELETE | `/api/v1/automation/macros/{id}` | Delete macro |

## Event Bus Events

`AutomationCreated`, `AutomationQueued`, `AutomationStarted`, `AutomationPaused`, `AutomationResumed`, `AutomationApprovalRequested`, `AutomationApproved`, `AutomationRejected`, `AutomationStepStarted`, `AutomationStepCompleted`, `AutomationRetry`, `AutomationRollback`, `AutomationCompleted`, `AutomationFailed`, `AutomationCancelled`, `AutomationScheduled`

## Templates

4 built-in templates: `open_browser_and_screenshot`, `file_backup`, `system_info`, `docker_status`

## New Files (28)

```
automation/
├── __init__.py
├── register_actions.py
├── engine/ (14 files)
├── browser/controller.py
├── windows/controller.py
├── filesystem/controller.py
├── terminal/controller.py
├── docker/controller.py
├── database/controller.py
├── printer/controller.py
├── office/controller.py
├── recorder/controller.py
├── policies/engine.py
├── validators/workflow_validator.py
├── templates/manager.py + 4 JSON templates
└── permissions/__init__.py

network/routes/automation.py
desktop/pages/automation.py
```

## Modified Files

```
network/api/server.py       # Automation router + engine start/stop
network/websocket/events.py # 16 automation events added
core/event_store.py         # Automation events in CATEGORY_MAP
desktop/window.py           # Automation page in sidebar
app/startup.py              # data/macros + data/artifacts dirs
```

## Verified

- 102 routes total (up from 75)
- All 27 automation endpoints return 200
- Workflow validation works (valid + invalid detection)
- Workflow creation and registration works
- Sync execution works (Test Workflow → completed in 8.76ms)
- History records execution with steps, duration, status
- Scheduling works (recurring job created)
- 38 policies loaded with risk levels
- 4 templates available
- Queue manager running with 2 workers
- Scheduler running
- All action handlers registered (browser, windows, fs, terminal, docker, db, printer, office, macro)
- Automation events published to EventBus
- Printer module gracefully handles missing pywin32

## Install Dependencies (optional, per module)

```bash
pip install playwright && playwright install    # Browser
pip install pywin32                               # Windows/Printer
pip install Pillow                                # Screenshots
pip install pycaw                                 # Audio
pip install python-docx openpyxl python-pptx fpdf2  # Office
pip install PyMuPDF                               # PDF reading
pip install pyautogui                             # Macro recorder
pip install send2trash                            # Recycle bin
pip install pymysql psycopg2-binary               # MySQL/PostgreSQL
```
