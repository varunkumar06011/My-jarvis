from fastapi import APIRouter, Depends, HTTPException

from core.event_bus import bus
from core.service_registry import registry
from network.api.authentication import require_perm
from network.api.schemas import VoiceRequest, VoiceResponse

router = APIRouter(prefix="/api/v1", tags=["voice"])


@router.post("/voice", response_model=VoiceResponse)
async def voice(request: VoiceRequest, auth: dict = Depends(require_perm("voice"))):
    """Speak text through Jarvis TTS."""
    try:
        tts = registry.get("tts")
    except KeyError:
        raise HTTPException(status_code=503, detail="TTS service not available")

    bus.publish("SpeechStarted", {"text": request.text, "client": auth["client"]})

    import threading
    thread = threading.Thread(target=tts.speak, args=(request.text,), daemon=True)
    thread.start()

    return VoiceResponse(status="speaking", text=request.text)
