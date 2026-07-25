from fastapi import APIRouter, Query
from pydantic import BaseModel

from sync.manager import sync_manager

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


class DeviceRegister(BaseModel):
    name: str
    device_type: str
    platform: str
    capabilities: list[str] = []


class SyncPush(BaseModel):
    data_type: str
    payload: dict


@router.post("/devices/register")
async def register_device(req: DeviceRegister):
    d = sync_manager.register_device(req.name, req.device_type, req.platform, req.capabilities)
    return d.to_dict()


@router.get("/devices")
async def list_devices():
    return {"devices": sync_manager.list_devices()}


@router.delete("/devices/{device_id}")
async def remove_device(device_id: str):
    ok = sync_manager.remove_device(device_id)
    return {"status": "ok" if ok else "not_found"}


@router.post("/devices/{device_id}/heartbeat")
async def heartbeat(device_id: str):
    ok = sync_manager.heartbeat(device_id)
    return {"status": "alive" if ok else "not_found"}


@router.post("/devices/{device_id}/push")
async def push_sync(device_id: str, req: SyncPush):
    sp = sync_manager.push(device_id, req.data_type, req.payload)
    return sp.to_dict()


@router.get("/devices/{device_id}/pull")
async def pull_sync(device_id: str, since_version: int = Query(0)):
    return {"updates": sync_manager.pull(device_id, since_version)}


@router.get("/log")
async def sync_log(limit: int = Query(50)):
    return {"log": sync_manager.get_sync_log(limit)}


@router.get("/stats")
async def sync_stats():
    return sync_manager.stats()
