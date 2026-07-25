import threading
import time

from fastapi import APIRouter, Depends, HTTPException

from core.event_bus import bus
from core.service_registry import registry
from network.api.authentication import require_perm
from network.api.backup import backup_manager
from network.api.config_migration import migrate_config, save_config_snapshot
from network.api.schemas import SuccessResponse

router = APIRouter(prefix="/api/v1", tags=["system"])


@router.post("/restart", response_model=SuccessResponse)
async def restart_services(auth: dict = Depends(require_perm("admin"))):
    """Gracefully restart Jarvis services."""
    bus.publish("TaskStarted", {"name": "service_restart", "client": auth["client"]})

    # Re-register health checks
    try:
        health_mgr = registry.get("health")
        health_mgr.stop()
        time.sleep(0.5)
        health_mgr.start()
    except KeyError:
        pass

    # Reload plugins
    try:
        from core.tool_registry import TOOLS, _discover_tools
        new_tools = _discover_tools()
        TOOLS.clear()
        TOOLS.update(new_tools)
        if registry.has("tools"):
            registry.remove("tools")
        registry.register("tools", TOOLS)
        bus.publish("PluginLoaded", {"count": len(TOOLS), "plugins": list(TOOLS.keys())})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restart failed: {e}")

    bus.publish("TaskCompleted", {"name": "service_restart"})
    return SuccessResponse(status="restarted", message="Services restarted successfully")


@router.post("/backup", tags=["system"])
async def create_backup(auth: dict = Depends(require_perm("admin"))):
    """Create a backup of settings and memory."""
    result = backup_manager.create_backup()
    return result


@router.get("/backups", tags=["system"])
async def list_backups(auth: dict = Depends(require_perm("admin"))):
    """List all available backups."""
    return backup_manager.list_backups()


@router.post("/backup/restore/{backup_id}", tags=["system"])
async def restore_backup(backup_id: str, auth: dict = Depends(require_perm("admin"))):
    """Restore from a backup."""
    result = backup_manager.restore_backup(backup_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete("/backup/{backup_id}", tags=["system"])
async def delete_backup(backup_id: str, auth: dict = Depends(require_perm("admin"))):
    """Delete a backup."""
    result = backup_manager.delete_backup(backup_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/config/migration", tags=["system"])
async def check_config_migration(auth: dict = Depends(require_perm("settings"))):
    """Check config migration status."""
    return migrate_config()


@router.post("/config/snapshot", tags=["system"])
async def create_config_snapshot(auth: dict = Depends(require_perm("settings"))):
    """Save current config as a snapshot."""
    snapshot = save_config_snapshot()
    return {"status": "saved", "version": snapshot["version"]}
