from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from core.service_registry import registry
from network.api.authentication import require_perm

router = APIRouter(prefix="/api/v1", tags=["projects"])


class ProjectRegisterRequest(BaseModel):
    name: Optional[str] = None
    root_path: str = Field(..., min_length=1)
    github_repo: Optional[str] = None
    framework: Optional[str] = None
    language: Optional[str] = None
    database: Optional[str] = None
    description: Optional[str] = None


class ProjectSwitchRequest(BaseModel):
    name: str = Field(..., min_length=1)


class ProjectResponse(BaseModel):
    name: str
    root_path: str
    github_repo: str = ""
    framework: str = ""
    language: str = ""
    database: str = ""
    architecture: str = ""
    description: str = ""
    tags: list = []
    is_active: bool = False


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    active: Optional[str] = None
    count: int


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(auth: dict = Depends(require_perm("read"))):
    """List all registered projects."""
    try:
        pm = registry.get("project_manager")
    except KeyError:
        raise HTTPException(status_code=503, detail="Project manager not available")

    projects = pm.list_projects()
    active = pm.get_active()
    active_name = active.name if active else None

    return ProjectListResponse(
        projects=[ProjectResponse(**{**p, "is_active": active_name == p["name"]}) for p in projects],
        active=active_name,
        count=len(projects),
    )


@router.post("/projects/register", response_model=ProjectResponse)
async def register_project(request: ProjectRegisterRequest, auth: dict = Depends(require_perm("admin"))):
    """Register a new project."""
    try:
        pm = registry.get("project_manager")
    except KeyError:
        raise HTTPException(status_code=503, detail="Project manager not available")

    info = pm.auto_detect(request.root_path)
    name = request.name or info.get("name", "project")

    project = pm.register(
        name=name,
        root_path=request.root_path,
        github_repo=request.github_repo or info.get("github_repo", ""),
        framework=request.framework or info.get("framework", ""),
        language=request.language or info.get("language", ""),
        database=request.database or info.get("database", ""),
        description=request.description or "",
    )

    return ProjectResponse(**{**project.to_dict(), "is_active": False})


@router.post("/projects/switch", response_model=ProjectResponse)
async def switch_project(request: ProjectSwitchRequest, auth: dict = Depends(require_perm("chat"))):
    """Switch to a registered project."""
    try:
        pm = registry.get("project_manager")
    except KeyError:
        raise HTTPException(status_code=503, detail="Project manager not available")

    project = pm.switch(request.name)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{request.name}' not found")

    return ProjectResponse(**{**project.to_dict(), "is_active": True})


@router.get("/projects/active", response_model=Optional[ProjectResponse])
async def get_active_project(auth: dict = Depends(require_perm("read"))):
    """Get the currently active project."""
    try:
        pm = registry.get("project_manager")
    except KeyError:
        raise HTTPException(status_code=503, detail="Project manager not available")

    project = pm.get_active()
    if not project:
        return None

    return ProjectResponse(**{**project.to_dict(), "is_active": True})


@router.delete("/projects/{name}")
async def remove_project(name: str, auth: dict = Depends(require_perm("admin"))):
    """Remove a project from the registry."""
    try:
        pm = registry.get("project_manager")
    except KeyError:
        raise HTTPException(status_code=503, detail="Project manager not available")

    removed = pm.remove(name)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")

    return {"status": "removed", "name": name}
