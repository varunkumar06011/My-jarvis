from fastapi import APIRouter, Depends

import configs.config as config
from network.api.authentication import require_perm
from network.api.schemas import SettingsResponse, SettingsUpdate, SettingsUpdateResponse

router = APIRouter(prefix="/api/v1", tags=["settings"])


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(auth: dict = Depends(require_perm("read"))):
    """Get current Jarvis configuration."""
    return SettingsResponse(
        model_name=config.MODEL_NAME,
        gpu_layers=config.GPU_LAYERS,
        whisper_model=config.WHISPER_MODEL,
        sample_rate=config.SAMPLE_RATE,
        wake_word=config.WAKE_WORD,
        wake_threshold=config.WAKE_THRESHOLD,
        version=config.VERSION,
    )


@router.post("/settings", response_model=SettingsUpdateResponse)
async def update_settings(update: SettingsUpdate, auth: dict = Depends(require_perm("settings"))):
    """Update Jarvis configuration at runtime."""
    updated = []

    if update.model_name is not None:
        config.MODEL_NAME = update.model_name
        updated.append("model_name")

    if update.gpu_layers is not None:
        config.GPU_LAYERS = update.gpu_layers
        updated.append("gpu_layers")

    if update.whisper_model is not None:
        config.WHISPER_MODEL = update.whisper_model
        updated.append("whisper_model")

    if update.wake_word is not None:
        config.WAKE_WORD = update.wake_word
        updated.append("wake_word")

    if update.wake_threshold is not None:
        config.WAKE_THRESHOLD = update.wake_threshold
        updated.append("wake_threshold")

    return SettingsUpdateResponse(status="updated", updated=updated)
