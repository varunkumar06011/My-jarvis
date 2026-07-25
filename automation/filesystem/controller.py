import hashlib
import os
import shutil
from pathlib import Path
from typing import Any, Optional

from automation.engine.context import AutomationContext
from automation.engine.rollback import RollbackManager
from automation.engine.artifacts import artifact_manager


class FilesystemEngine:
    """Filesystem automation with rollback support for destructive operations."""

    def read(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        path = params.get("path", "")
        encoding = params.get("encoding", "utf-8")
        content = Path(path).read_text(encoding=encoding)
        return {"status": "ok", "path": path, "content": content[:5000], "length": len(content)}

    def read_binary(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        path = params.get("path", "")
        data = Path(path).read_bytes()
        return {"status": "ok", "path": path, "size": len(data)}

    def write(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        path = params.get("path", "")
        content = params.get("content", "")
        encoding = params.get("encoding", "utf-8")
        p = Path(path)

        # Backup for rollback
        if p.exists():
            old_content = p.read_text(encoding=encoding)
            rollback.register(
                "fs.write",
                lambda: p.write_text(old_content, encoding=encoding),
                f"Restore original content of {path}",
            )
        else:
            rollback.register(
                "fs.write",
                lambda: p.unlink(missing_ok=True),
                f"Delete created file {path}",
            )

        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding=encoding)
        return {"status": "ok", "path": path, "bytes": len(content)}

    def copy(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        src = params.get("src", "")
        dst = params.get("dst", "")
        shutil.copy2(src, dst)
        rollback.register(
            "fs.copy",
            lambda: Path(dst).unlink(missing_ok=True),
            f"Delete copied file {dst}",
        )
        return {"status": "ok", "src": src, "dst": dst}

    def move(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        src = params.get("src", "")
        dst = params.get("dst", "")
        shutil.move(src, dst)
        rollback.register(
            "fs.move",
            lambda: shutil.move(dst, src),
            f"Move {dst} back to {src}",
        )
        return {"status": "ok", "src": src, "dst": dst}

    def rename(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        src = params.get("src", "")
        dst = params.get("dst", "")
        os.rename(src, dst)
        rollback.register(
            "fs.rename",
            lambda: os.rename(dst, src),
            f"Rename {dst} back to {src}",
        )
        return {"status": "ok", "src": src, "dst": dst}

    def delete(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        path = params.get("path", "")
        use_recycle = params.get("recycle", True)
        p = Path(path)

        if use_recycle:
            try:
                from send2trash import send2trash
                send2trash(str(p))
                rollback.register(
                    "fs.delete",
                    lambda: None,  # Can't easily undo recycle bin
                    f"File {path} sent to recycle bin",
                )
                return {"status": "ok", "path": path, "method": "recycle"}
            except ImportError:
                pass

        # Permanent delete with backup
        if p.is_file():
            backup = p.read_bytes()
            p.unlink()
            rollback.register(
                "fs.delete",
                lambda: p.write_bytes(backup),
                f"Restore deleted file {path}",
            )
        elif p.is_dir():
            import tempfile, zipfile
            backup_path = Path(tempfile.gettempdir()) / f"jarvis_backup_{p.name}.zip"
            with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in p.rglob("*"):
                    zf.write(f, f.relative_to(p.parent))
            shutil.rmtree(p)
            rollback.register(
                "fs.delete",
                lambda: shutil.unpack_archive(backup_path, p.parent),
                f"Restore deleted directory {path}",
            )

        return {"status": "ok", "path": path, "method": "permanent"}

    def search(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        directory = params.get("directory", ".")
        pattern = params.get("pattern", "*")
        recursive = params.get("recursive", True)
        limit = params.get("limit", 100)

        results = []
        base = Path(directory)
        if recursive:
            for p in base.rglob(pattern):
                results.append(str(p))
                if len(results) >= limit:
                    break
        else:
            for p in base.glob(pattern):
                results.append(str(p))
                if len(results) >= limit:
                    break

        return {"status": "ok", "count": len(results), "files": results}

    def hash_file(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        path = params.get("path", "")
        algo = params.get("algorithm", "sha256")
        h = hashlib.new(algo)
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return {"status": "ok", "path": path, "algorithm": algo, "hash": h.hexdigest()}

    def compress(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        import zipfile
        src = params.get("src", "")
        dst = params.get("dst", "")
        with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zf:
            p = Path(src)
            if p.is_file():
                zf.write(p, p.name)
            elif p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file():
                        zf.write(f, f.relative_to(p))
        return {"status": "ok", "src": src, "dst": dst}

    def extract(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        import zipfile
        src = params.get("src", "")
        dst = params.get("dst", ".")
        with zipfile.ZipFile(src, "r") as zf:
            zf.extractall(dst)
        return {"status": "ok", "src": src, "dst": dst}

    def list_dir(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        path = params.get("path", ".")
        p = Path(path)
        items = []
        for item in p.iterdir():
            items.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else 0,
            })
        return {"status": "ok", "path": path, "items": items}


filesystem_engine = FilesystemEngine()
