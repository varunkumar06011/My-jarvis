from fastapi import APIRouter, Depends

from core.service_registry import registry
from network.api.authentication import authenticate
from network.api.schemas import HealthResponse, HealthStatus

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(auth: dict = Depends(authenticate)):
    """Check Jarvis health status."""
    try:
        health_mgr = registry.get("health")
        results = health_mgr.run_all_checks()
    except KeyError:
        results = {}

    if not results:
        return HealthResponse(status=HealthStatus.UNAVAILABLE, services={})

    all_healthy = all(results.values())
    any_healthy = any(results.values())

    if all_healthy:
        status = HealthStatus.HEALTHY
    elif any_healthy:
        status = HealthStatus.DEGRADED
    else:
        status = HealthStatus.UNAVAILABLE

    return HealthResponse(status=status, services=results)
