from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional

from network.api.authentication import authenticate

router = APIRouter(prefix="/api/v1/automation/plugins", tags=["automation-plugins"])


def _get_loader():
    from automation.plugins.base import plugin_loader
    return plugin_loader


@router.get("")
async def list_plugins(auth: dict = Depends(authenticate)):
    loader = _get_loader()
    return loader.list_plugins()


@router.get("/{plugin_name}")
async def get_plugin(plugin_name: str, auth: dict = Depends(authenticate)):
    loader = _get_loader()
    plugin = loader.get_plugin(plugin_name)
    if plugin is None:
        return {"error": "Plugin not found", "plugin": plugin_name}
    return plugin.to_dict()


@router.get("/{plugin_name}/workflows")
async def get_plugin_workflows(plugin_name: str, auth: dict = Depends(authenticate)):
    loader = _get_loader()
    plugin = loader.get_plugin(plugin_name)
    if plugin is None:
        return {"error": "Plugin not found"}
    return {"workflows": plugin.workflows}


@router.get("/{plugin_name}/actions")
async def get_plugin_actions(plugin_name: str, auth: dict = Depends(authenticate)):
    loader = _get_loader()
    plugin = loader.get_plugin(plugin_name)
    if plugin is None:
        return {"error": "Plugin not found"}
    return {"actions": list(plugin.actions.keys()), "policies": {k: v.to_dict() for k, v in plugin.policies.items()}}


@router.post("/reload")
async def reload_plugins(auth: dict = Depends(authenticate)):
    loader = _get_loader()
    loaded = loader.load_all()
    return {"status": "ok", "loaded": loaded, "count": len(loaded)}
