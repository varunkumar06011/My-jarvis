from fastapi import APIRouter, Depends, HTTPException

from core.event_bus import bus
from core.service_registry import registry
from network.api.authentication import require_perm
from network.api.schemas import VoiceRequest, VoiceResponse, RepoQueryRequest, RepoQueryResponse

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


@router.post("/repo-query", response_model=RepoQueryResponse)
async def repo_query(request: RepoQueryRequest, auth: dict = Depends(require_perm("chat"))):
    """Ask a repository-aware question. Routes through the Repository Voice Bridge."""
    from services.repo_bridge import handle_repo_query, classify_intent

    intent = classify_intent(request.query)
    response = handle_repo_query(request.query)

    if response is None:
        return RepoQueryResponse(intent=None, response="", is_repo_query=False)

    return RepoQueryResponse(intent=intent, response=response, is_repo_query=True)
