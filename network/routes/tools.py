from fastapi import APIRouter, Depends, HTTPException

from core.event_bus import bus
from core.service_registry import registry
from core.tool_executor import execute as execute_tool
from network.api.authentication import require_perm
from network.api.schemas import ToolRequest, ToolResponse
from network.security.audit import audit_logger

router = APIRouter(prefix="/api/v1", tags=["tools"])


@router.post("/tool", response_model=ToolResponse)
async def execute(request: ToolRequest, auth: dict = Depends(require_perm("execute_tools"))):
    """Execute a Jarvis tool/plugin."""
    try:
        tools = registry.get("tools")
    except KeyError:
        raise HTTPException(status_code=503, detail="Tools service not available")

    if request.tool not in tools:
        raise HTTPException(status_code=404, detail=f"Tool '{request.tool}' not found")

    audit_logger.tool_executed(auth["client"], request.tool, request.input or "")

    bus.publish("TaskStarted", {"name": f"tool:{request.tool}", "client": auth["client"]})

    try:
        if request.input:
            result = execute_tool(request.tool, request.input)
        else:
            result = execute_tool(request.tool)
    except Exception as e:
        bus.publish("TaskFailed", {"name": f"tool:{request.tool}", "error": str(e)})
        return ToolResponse(tool=request.tool, result="", error=str(e))

    bus.publish("ToolExecuted", {
        "tool": request.tool,
        "input": request.input,
        "result": result,
        "client": auth["client"],
    })

    return ToolResponse(tool=request.tool, result=result)
