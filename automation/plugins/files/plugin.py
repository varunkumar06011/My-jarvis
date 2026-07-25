import hashlib
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from automation.engine.context import AutomationContext
from automation.engine.rollback import RollbackManager
from automation.engine.artifacts import artifact_manager
from automation.plugins.base import AutomationPlugin, RiskLevel


class FileOrgPlugin(AutomationPlugin):
    """File organization automation plugin."""

    def __init__(self):
        super().__init__()
        self.name = "FileOrganization"
        self.description = "Sort, deduplicate, archive, sync folders"
        self.version = "1.0"
        self.author = "Jarvis"

    def initialize(self):
        self.register_action("files.sort_by_type", self.sort_by_type, RiskLevel.MEDIUM, requires_rollback=True)
        self.register_action("files.sort_by_date", self.sort_by_date, RiskLevel.MEDIUM, requires_rollback=True)
        self.register_action("files.deduplicate", self.deduplicate, RiskLevel.MEDIUM, requires_rollback=True)
        self.register_action("files.archive", self.archive_old, RiskLevel.MEDIUM, requires_rollback=True)
        self.register_action("files.sync_folders", self.sync_folders, RiskLevel.MEDIUM, requires_rollback=True)
        self.register_action("files.find_large", self.find_large_files, RiskLevel.SAFE)
        self.register_action("files.find_empty_dirs", self.find_empty_dirs, RiskLevel.SAFE)
        self.register_action("files.rename_batch", self.rename_batch, RiskLevel.MEDIUM, requires_rollback=True)
        self.register_action("files.organize_downloads", self.organize_downloads, RiskLevel.MEDIUM, requires_rollback=True)

        self.register_workflow({
            "id": "files_cleanup_workflow",
            "name": "File Cleanup Workflow",
            "description": "Find large files, deduplicate, archive old, organize",
            "version": "1.0",
            "variables": {"target_dir": "C:/Users/Downloads"},
            "steps": [
                {"name": "find_large", "type": "action", "action": "files.find_large", "params": {"directory": "{{target_dir}}", "min_size_mb": 100}},
                {"name": "deduplicate", "type": "action", "action": "files.deduplicate", "params": {"directory": "{{target_dir}}"}},
                {"name": "organize", "type": "action", "action": "files.organize_downloads", "params": {"directory": "{{target_dir}}"}},
            ],
        })

    def sort_by_type(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        directory = Path(params.get("directory", "."))
        moved = 0
        for item in directory.iterdir():
            if item.is_file():
                ext = item.suffix.lower().lstrip(".") or "misc"
                target_dir = directory / ext
                target_dir.mkdir(exist_ok=True)
                target = target_dir / item.name
                shutil.move(str(item), str(target))
                rollback.register("files.sort", lambda i=item, t=target: shutil.move(str(t), str(i)), f"Move {item.name} back")
                moved += 1
        return {"status": "ok", "moved": moved}

    def sort_by_date(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        directory = Path(params.get("directory", "."))
        moved = 0
        for item in directory.iterdir():
            if item.is_file():
                mtime = datetime.fromtimestamp(item.stat().st_mtime)
                target_dir = directory / mtime.strftime("%Y-%m")
                target_dir.mkdir(exist_ok=True)
                target = target_dir / item.name
                shutil.move(str(item), str(target))
                moved += 1
        return {"status": "ok", "moved": moved}

    def deduplicate(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        directory = Path(params.get("directory", "."))
        hashes: dict[str, Path] = {}
        duplicates = 0
        for item in directory.rglob("*"):
            if item.is_file():
                h = hashlib.md5(item.read_bytes()).hexdigest()
                if h in hashes:
                    item.unlink()
                    duplicates += 1
                else:
                    hashes[h] = item
        return {"status": "ok", "duplicates_removed": duplicates, "unique_files": len(hashes)}

    def archive_old(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        directory = Path(params.get("directory", "."))
        days = params.get("days", 30)
        archive_dir = directory / "archive"
        archive_dir.mkdir(exist_ok=True)
        cutoff = datetime.now().timestamp() - (days * 86400)
        archived = 0
        for item in directory.iterdir():
            if item.is_file() and item.stat().st_mtime < cutoff:
                shutil.move(str(item), str(archive_dir / item.name))
                archived += 1
        return {"status": "ok", "archived": archived, "archive_dir": str(archive_dir)}

    def sync_folders(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        src = Path(params.get("source", ""))
        dst = Path(params.get("destination", ""))
        synced = 0
        for item in src.rglob("*"):
            if item.is_file():
                rel = item.relative_to(src)
                target = dst / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists() or target.stat().st_size != item.stat().st_size:
                    shutil.copy2(str(item), str(target))
                    synced += 1
        return {"status": "ok", "synced": synced, "source": str(src), "destination": str(dst)}

    def find_large_files(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        directory = Path(params.get("directory", "."))
        min_size = params.get("min_size_mb", 100) * 1024 * 1024
        large_files = []
        for item in directory.rglob("*"):
            if item.is_file() and item.stat().st_size >= min_size:
                large_files.append({
                    "path": str(item),
                    "size_mb": round(item.stat().st_size / 1024 / 1024, 2),
                })
        large_files.sort(key=lambda x: x["size_mb"], reverse=True)
        return {"status": "ok", "count": len(large_files), "files": large_files[:50]}

    def find_empty_dirs(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        directory = Path(params.get("directory", "."))
        empty = []
        for item in directory.rglob("*"):
            if item.is_dir():
                try:
                    next(item.iterdir())
                except StopIteration:
                    empty.append(str(item))
        return {"status": "ok", "count": len(empty), "empty_dirs": empty}

    def rename_batch(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        directory = Path(params.get("directory", "."))
        pattern = params.get("pattern", "{index}_{name}")
        prefix = params.get("prefix", "")
        start_index = params.get("start_index", 1)
        renamed = 0
        for i, item in enumerate(sorted(directory.iterdir()), start_index):
            if item.is_file():
                new_name = pattern.format(index=i, name=item.stem, ext=item.suffix, prefix=prefix)
                new_path = item.parent / new_name
                old_name = item.name
                item.rename(new_path)
                rollback.register("files.rename", lambda np=new_path, on=old_name: np.rename(np.parent / on), f"Rename {new_name} back to {old_name}")
                renamed += 1
        return {"status": "ok", "renamed": renamed}

    def organize_downloads(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        directory = Path(params.get("directory", "."))
        categories = {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"],
            "Documents": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv"],
            "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv"],
            "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg"],
            "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
            "Code": [".py", ".js", ".ts", ".java", ".cpp", ".c", ".html", ".css", ".json", ".xml"],
            "Installers": [".exe", ".msi", ".dmg", ".deb", ".rpm"],
        }
        moved = 0
        for item in directory.iterdir():
            if item.is_file():
                ext = item.suffix.lower()
                for category, exts in categories.items():
                    if ext in exts:
                        target_dir = directory / category
                        target_dir.mkdir(exist_ok=True)
                        target = target_dir / item.name
                        if not target.exists():
                            shutil.move(str(item), str(target))
                            moved += 1
                        break
        return {"status": "ok", "moved": moved, "categories": list(categories.keys())}
