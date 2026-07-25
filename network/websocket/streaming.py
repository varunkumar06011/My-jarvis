import asyncio
from typing import AsyncGenerator

from fastapi import WebSocket


async def stream_response(text: str, chunk_size: int = 3) -> AsyncGenerator[str, None]:
    """Simulate token-by-token streaming for a complete response string."""
    words = text.split(" ")
    for i, word in enumerate(words):
        chunk = word + (" " if i < len(words) - 1 else "")
        yield chunk
        await asyncio.sleep(0.03)


async def stream_to_websocket(websocket: WebSocket, text: str):
    """Stream a response token-by-token over a WebSocket connection."""
    async for chunk in stream_response(text):
        import json, time
        msg = json.dumps({
            "event": "StreamChunk",
            "data": {"token": chunk, "done": False},
            "timestamp": time.time(),
        })
        await websocket.send_text(msg)

    import json, time
    done_msg = json.dumps({
        "event": "StreamChunk",
        "data": {"token": "", "done": True},
        "timestamp": time.time(),
    })
    await websocket.send_text(done_msg)
