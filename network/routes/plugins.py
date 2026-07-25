import importlib

from fastapi import APIRouter, Depends, HTTPException

from core.event_bus import bus
from core.service_registry import registry
from core.tool_registry import TOOLS, _discover_tools
from network.api.authentication import require_perm
from network.api.schemas import PluginInfo, PluginsResponse, PluginReloadResponse

router = APIRouter(prefix="/api/v1", tags=["plugins"])


@router.get("/plugins", response_model=PluginsResponse)
async def list_plugins(auth: dict = Depends(require_perm("plugins"))):
    """List all loaded Jarvis plugins/tools."""
    plugins = []
    for name, module in TOOLS.items():
        info = module.TOOL
        plugins.append(PluginInfo(
            name=info.get("name", name),
            description=info.get("description", ""),
        ))

    return PluginsResponse(plugins=plugins, count=len(plugins))


@router.post("/plugins/reload", response_model=PluginReloadResponse)
async def reload_plugins(auth: dict = Depends(require_perm("plugins"))):
    """Reload all plugins."""
    import core.tool_registry as tr

    new_tools = _discover_tools()

    # Update the global TOOLS dict in-place
    TOOLS.clear()
    TOOLS.update(new_tools)

    # Update registry
    if registry.has("tools"):
        registry.remove("tools")
    registry.register("tools", TOOLS)

    plugin_names = list(TOOLS.keys())
    bus.publish("PluginLoaded", {"count": len(TOOLS), "plugins": plugin_names})

    return PluginReloadResponse(
        status="reloaded",
        count=len(TOOLS),
        plugins=plugin_names,
    )
