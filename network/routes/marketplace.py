from fastapi import APIRouter, Query
from pydantic import BaseModel

from marketplace.registry import marketplace

router = APIRouter(prefix="/api/v1/marketplace", tags=["marketplace"])


class PublishPlugin(BaseModel):
    name: str
    version: str
    category: str
    description: str
    author: str = ""
    dependencies: list[str] = []
    permissions: list[str] = []
    signature: str = ""
    checksum: str = ""


@router.get("/discover")
async def discover(category: str = "", query: str = "", limit: int = 20):
    return {"plugins": marketplace.discover(category, query, limit)}


@router.get("/categories")
async def categories():
    return {"categories": marketplace.get_categories()}


@router.post("/publish")
async def publish(req: PublishPlugin):
    m = marketplace.publish(req.name, req.version, req.category, req.description,
                           req.author, req.dependencies, req.permissions,
                           req.signature, req.checksum)
    return m.to_dict()


@router.post("/install/{manifest_id}")
async def install(manifest_id: str):
    return marketplace.install(manifest_id)


@router.post("/uninstall/{name}")
async def uninstall(name: str):
    return marketplace.uninstall(name)


@router.post("/enable/{name}")
async def enable(name: str):
    return marketplace.enable(name)


@router.post("/disable/{name}")
async def disable(name: str):
    return marketplace.disable(name)


@router.get("/installed")
async def list_installed():
    return {"installed": marketplace.list_installed()}


@router.get("/updates")
async def check_updates():
    return {"updates": marketplace.check_updates()}


@router.post("/update/{name}")
async def update_plugin(name: str):
    return marketplace.update(name)


@router.get("/stats")
async def stats():
    return marketplace.stats()
