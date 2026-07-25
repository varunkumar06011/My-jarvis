import psutil

from fastapi import APIRouter, Depends

from configs.config import MODEL_NAME, VERSION, WAKE_WORD
from core.service_registry import registry
from core.task_queue import task_queue
from network.api.authentication import authenticate
from network.api.schemas import StatusResponse

router = APIRouter(prefix="/api/v1", tags=["status"])


@router.get("/status", response_model=StatusResponse)
async def status(auth: dict = Depends(authenticate)):
    """Get current Jarvis status."""
    lifecycle_state = "Unknown"
    if registry.has("lifecycle"):
        lifecycle = registry.get("lifecycle")
        lifecycle_state = lifecycle.state.value

    wake_word_state = "inactive"
    if registry.has("wake_word"):
        wake_word_state = "active"

    plugin_count = 0
    if registry.has("tools"):
        plugin_count = len(registry.get("tools"))

    queue_size = task_queue.pending_count()

    cpu_percent = psutil.cpu_percent(interval=0.5)
    ram_percent = psutil.virtual_memory().percent

    return StatusResponse(
        lifecycle=lifecycle_state,
        model=MODEL_NAME,
        wake_word=wake_word_state,
        plugin_count=plugin_count,
        queue_size=queue_size,
        cpu_percent=cpu_percent,
        ram_percent=ram_percent,
        version=VERSION,
    )
