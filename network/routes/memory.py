from fastapi import APIRouter, Depends, HTTPException

from core.service_registry import registry
from memory.storage import load_history, list_sessions
from network.api.authentication import require_perm
from network.api.schemas import MemoryEntry, MemoryResponse

router = APIRouter(prefix="/api/v1", tags=["memory"])


@router.get("/memory", response_model=MemoryResponse)
async def get_memory(session: str = "default", auth: dict = Depends(require_perm("read"))):
    """Get conversation memory/history for a session."""
    history = load_history(session)
    entries = [MemoryEntry(role=m["role"], content=m["content"]) for m in history]
    return MemoryResponse(session=session, entries=entries, count=len(entries))


@router.get("/memory/sessions", response_model=list[str])
async def get_sessions(auth: dict = Depends(require_perm("read"))):
    """List all saved memory sessions."""
    return list_sessions()
