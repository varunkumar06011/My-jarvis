import asyncio
import json
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from core.event_bus import bus
from core.service_registry import registry
from core.task_queue import task_queue
from network.api.authentication import authenticate, require_perm
from network.api.schemas import ChatRequest, ChatResponse, ChatStreamChunk

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, auth: dict = Depends(require_perm("chat"))):
    """Send a message to Jarvis and get a response."""
    try:
        llm = registry.get("llm")
    except KeyError:
        raise HTTPException(status_code=503, detail="LLM service not available")

    bus.publish("TaskStarted", {"name": "chat", "client": auth["client"]})

    future = task_queue.submit("chat", llm.chat, request.message)
    result = future.result(timeout=120)

    bus.publish("LLMResponse", {
        "input": request.message,
        "response": result,
        "client": auth["client"],
    })

    return ChatResponse(response=result, session=request.session)


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, auth: dict = Depends(require_perm("chat"))):
    """Stream a chat response token-by-token."""
    try:
        llm = registry.get("llm")
    except KeyError:
        raise HTTPException(status_code=503, detail="LLM service not available")

    bus.publish("TaskStarted", {"name": "chat_stream", "client": auth["client"]})

    future = task_queue.submit("chat", llm.chat, request.message)
    full_response = future.result(timeout=120)

    bus.publish("LLMResponse", {
        "input": request.message,
        "response": full_response,
        "client": auth["client"],
    })

    async def generate():
        from network.websocket.streaming import stream_response
        async for chunk in stream_response(full_response):
            yield json.dumps({"token": chunk, "done": False}) + "\n"
        yield json.dumps({"token": "", "done": True}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
