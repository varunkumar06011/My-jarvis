from fastapi import APIRouter, Depends, Query

from core.event_store import EventCategory, EventStatus, event_store
from core.metrics import metrics
from core.telemetry import TelemetryLevel, telemetry
from core.structured_log import LogLevel, structured_logger
from core.recovery import recovery_engine
from flags import flag_manager
from network.api.authentication import authenticate

router = APIRouter(prefix="/api/v1", tags=["diagnostics"])


@router.get("/metrics")
async def get_metrics(auth: dict = Depends(authenticate)):
    """Get current metrics snapshot."""
    return metrics.snapshot()


@router.get("/performance")
async def get_performance(auth: dict = Depends(authenticate)):
    """Get performance summary with latency stats."""
    return metrics.performance_summary()


@router.get("/timeline")
async def get_timeline(
    auth: dict = Depends(authenticate),
    limit: int = Query(default=50, le=500),
):
    """Get event timeline (most recent first)."""
    return event_store.timeline(limit=limit)


@router.get("/events")
async def get_events(
    auth: dict = Depends(authenticate),
    category: str = Query(default=None),
    event: str = Query(default=None),
    status: str = Query(default=None),
    request_id: str = Query(default=None),
    session_id: str = Query(default=None),
    limit: int = Query(default=100, le=500),
):
    """Search events with filters."""
    cat = EventCategory(category) if category else None
    st = EventStatus(status) if status else None
    return event_store.search(
        category=cat,
        event=event,
        status=st,
        request_id=request_id,
        session_id=session_id,
        limit=limit,
    )


@router.get("/events/stats")
async def get_event_stats(auth: dict = Depends(authenticate)):
    """Get event statistics."""
    return event_store.statistics()


@router.get("/events/export")
async def export_events(auth: dict = Depends(authenticate)):
    """Export all events to a file."""
    path = event_store.export()
    return {"status": "exported", "path": str(path), "count": event_store.count()}


@router.get("/telemetry")
async def get_telemetry(
    auth: dict = Depends(authenticate),
    level: str = Query(default=None),
    category: str = Query(default=None),
    limit: int = Query(default=100, le=500),
):
    """Query telemetry entries."""
    lvl = TelemetryLevel(level) if level else None
    return telemetry.query(level=lvl, category=category, limit=limit)


@router.get("/telemetry/summary")
async def get_telemetry_summary(auth: dict = Depends(authenticate)):
    """Get telemetry summary."""
    return telemetry.summary()


@router.get("/logs")
async def get_logs(
    auth: dict = Depends(authenticate),
    level: str = Query(default=None),
    category: str = Query(default=None),
    limit: int = Query(default=100, le=500),
):
    """Query structured logs."""
    lvl = LogLevel(level) if level else None
    return structured_logger.query(level=lvl, category=category, limit=limit)


@router.get("/logs/summary")
async def get_logs_summary(auth: dict = Depends(authenticate)):
    """Get log level summary."""
    return structured_logger.summary()


@router.get("/recovery")
async def get_recovery_info(auth: dict = Depends(authenticate)):
    """Get recovery engine status and rules."""
    return {
        "rules": recovery_engine.get_rules(),
        "log": recovery_engine.get_recovery_log(),
    }


@router.get("/flags")
async def get_feature_flags(auth: dict = Depends(authenticate)):
    """List all feature flags."""
    return flag_manager.list_flags()


@router.post("/flags/{name}")
async def set_feature_flag(
    name: str,
    enabled: bool = Query(...),
    auth: dict = Depends(authenticate),
):
    """Enable or disable a feature flag."""
    flag_manager.set(name, enabled)
    return {"status": "updated", "flag": name, "enabled": enabled}
