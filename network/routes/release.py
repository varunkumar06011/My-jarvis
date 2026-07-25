from fastapi import APIRouter

from marketplace.release import release_manager

router = APIRouter(prefix="/api/v1/release", tags=["release"])


@router.get("/info")
async def release_info():
    return release_manager.release_info()


@router.post("/backup")
async def backup_config():
    return release_manager.backup_config()


@router.get("/backups")
async def list_backups():
    return {"backups": release_manager.list_backups()}


@router.post("/restore")
async def restore_config(backup_dir: str):
    return release_manager.restore_config(backup_dir)


@router.post("/build")
async def build_exe():
    return release_manager.build_exe()


@router.post("/tests")
async def run_tests():
    return release_manager.run_tests()


@router.post("/installer")
async def create_installer(version: str):
    path = release_manager.create_installer_script(version)
    return {"status": "ok", "path": str(path)}


@router.post("/tag")
async def create_tag(version: str):
    return release_manager.create_version_tag(version)
