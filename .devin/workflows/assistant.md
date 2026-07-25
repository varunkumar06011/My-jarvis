# Step 29 — Automation Plugins

## Goal

Build concrete automation plugins on top of the Step 28 Enterprise Automation Platform. Each plugin registers actions, workflows, and policies with the engine via a plugin loader framework.

## Plugin Framework

`automation/plugins/base.py` provides:
- `AutomationPlugin` — abstract base class with `register_action()`, `register_workflow()`, policy auto-registration
- `PluginLoader` — auto-discovers plugins in `automation/plugins/*/plugin.py`, loads them, and registers all actions/policies/workflows with the engine

## 8 Plugins — 94 Actions, 11 Workflows

### 1. Git Plugin (17 actions, 2 workflows)
- **Actions**: status, log, diff, branch, add, commit, push, pull, clone, stash, stash_pop, checkout, merge, create_branch, fetch, remote, init
- **Workflows**: `git_daily_workflow` (pull→status→add→commit), `git_feature_branch` (fetch→create→checkout)
- **Risk levels**: SAFE (status, log, diff, branch, clone, fetch, remote, init, create_branch) → MEDIUM (add, commit, pull, stash, checkout) → HIGH (push, merge)

### 2. GitHub Plugin (14 actions, 1 workflow)
- **Actions**: repos, repo_info, issues, create_issue, close_issue, pulls, create_pr, merge_pr, actions, trigger_action, releases, create_release, user, search
- **Workflow**: `github_review_workflow` (list PRs → approval gate → merge)
- **Risk levels**: SAFE (list/read) → HIGH (create issue/PR, trigger action) → CRITICAL (merge PR, create release)
- **Auth**: Uses `GITHUB_TOKEN` env var

### 3. Web Plugin (10 actions, 1 workflow)
- **Actions**: search, scrape, fill_form, login, click_and_wait, multi_page, extract_table, scroll, get_links, set_cookies
- **Workflow**: `web_search_and_scrape` (open→search→scrape→screenshot→close)
- **Built on**: Browser engine (Playwright)

### 4. System Plugin (15 actions, 1 workflow)
- **Actions**: cleanup_temp, disk_usage, disk_cleanup, list_services, service_status, start_service, stop_service, list_startup, enable_startup, disable_startup, system_info, network_info, env_vars, kill_process, create_restore_point
- **Workflow**: `system_daily_maintenance` (disk check→cleanup→services→network)
- **Risk levels**: SAFE (read) → MEDIUM (cleanup, disable startup) → HIGH (start/stop service, kill process, enable startup) → CRITICAL (restore point)

### 5. Restaurant/POS Plugin (10 actions, 2 workflows)
- **Actions**: print_receipt, daily_report, menu_sync, process_order, kot_print, bill_calc, table_status, inventory_check, sales_summary, generate_qr
- **Workflows**: `restaurant_end_of_day` (report→sales→inventory→approval→print PDF), `restaurant_order_flow` (process→KOT→bill→receipt)
- **Features**: Order calculation with tax, KOT printing, receipt printing, QR code generation

### 6. Development Plugin (11 actions, 2 workflows)
- **Actions**: create_project, run_tests, build, lint, format, install_deps, run_script, docker_build, deploy, check_ports, kill_port
- **Workflows**: `dev_ci_workflow` (install→lint→test→build), `dev_new_project` (create→git init→install)
- **Project types**: python, node, react, fastapi
- **Risk levels**: SAFE (tests, ports) → MEDIUM (build, format, install) → HIGH (kill_port) → CRITICAL (deploy)

### 7. File Organization Plugin (9 actions, 1 workflow)
- **Actions**: sort_by_type, sort_by_date, deduplicate, archive_old, sync_folders, find_large_files, find_empty_dirs, rename_batch, organize_downloads
- **Workflow**: `files_cleanup_workflow` (find large→deduplicate→organize)
- **Features**: MD5 dedup, category-based sorting, archive by date, folder sync

### 8. Notification Plugin (8 actions, 1 workflow)
- **Actions**: desktop_notification, toast_notification, play_sound, create_reminder, list_reminders, cancel_reminder, email_digest, log_event
- **Workflow**: `notify_morning_briefing` (disk check→desktop notification)
- **Features**: Windows toast notifications, sound alerts, persistent reminders, structured logging

## Policy Engine

132 total policies (38 core + 94 plugin):
- SAFE: 68 actions (read-only, status checks)
- MEDIUM: 38 actions (writes, modifications with rollback)
- HIGH: 20 actions (destructive, external pushes — requires approval)
- CRITICAL: 6 actions (deploy, merge PR, create release, restore point — requires approval)

## API Endpoints (5 new routes, 112 total)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/automation/plugins` | List all loaded plugins |
| GET | `/api/v1/automation/plugins/{name}` | Get plugin details |
| GET | `/api/v1/automation/plugins/{name}/workflows` | List plugin workflows |
| GET | `/api/v1/automation/plugins/{name}/actions` | List plugin actions and policies |
| POST | `/api/v1/automation/plugins/reload` | Reload all plugins |

## SDK Methods (20 new)

Automation: `start_automation`, `pause_automation`, `resume_automation`, `cancel_automation`, `rollback_automation`, `automation_status`, `automation_history`, `automation_workflows`, `create_workflow`, `automation_templates`, `validate_workflow`, `automation_queue`, `automation_approvals`, `approve_request`, `reject_request`, `schedule_automation`

Plugins: `list_plugins`, `get_plugin`, `plugin_workflows`, `plugin_actions`, `reload_plugins`

## New Files (20)

```
automation/plugins/
├── __init__.py
├── base.py                      # Plugin framework (AutomationPlugin + PluginLoader)
├── git/__init__.py + plugin.py
├── github/__init__.py + plugin.py
├── web/__init__.py + plugin.py
├── system/__init__.py + plugin.py
├── restaurant/__init__.py + plugin.py
├── dev/__init__.py + plugin.py
├── files/__init__.py + plugin.py
└── notify/__init__.py + plugin.py

network/routes/plugins_api.py    # Plugin API routes
```

## Modified Files (6)

```
automation/register_actions.py   # Plugin loading on startup
automation/engine/context.py     # Fixed variable resolution for list/dict types
network/api/server.py            # Plugin router + plugin_loader registration
network/clients/sdk.py           # 20 new SDK methods
app/startup.py                   # data/reminders directory
```

## Pre-existing Bugs Fixed (3)

```
ai/learning/decisions.py         # Missing DECISIONS_FILE constant
ai/learning/preferences.py       # Missing PREFERENCES_FILE constant
network/routes/learning.py       # `any` → `Any` (pydantic schema error)
```

## Verified at Runtime

- 112 routes total (up from 102)
- 8 plugins auto-discovered and loaded
- 94 plugin actions registered
- 11 plugin workflows registered
- 132 policies (38 core + 94 plugin)
- Restaurant Order Flow: completed — order TEST-001, subtotal=560, tax=28, total=588, 2 items
- Git Daily Workflow: completed in 1443ms
- System Daily Maintenance: completed in 19539ms
- File Cleanup Workflow: completed in 20ms
- All 4 tested workflows completed successfully
- History records all executions with duration and status
- Variable resolution fixed: list/dict variables passed through correctly

## Architecture

```
Step 28: Enterprise Automation Platform (engine, state machine, policies, queue, scheduler)
  ↓
Step 29: Automation Plugins (git, github, web, system, restaurant, dev, files, notify)
  ↓
Step 30+: Domain-specific automations (BookMyShow, VS Code, Slack, email, calendar, etc.)
```
