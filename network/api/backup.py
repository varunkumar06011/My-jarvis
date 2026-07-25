import json
import shutil
from datetime import datetime
from pathlib import Path

from configs.config import CONFIG_VERSION
from memory.storage import SESSION_DIR

BACKUP_DIR = Path("backups")
CONFIG_FILE = Path("data/config_snapshot.json")


class BackupManager:
    def __init__(self, backup_dir: Path = BACKUP_DIR):
        self._backup_dir = backup_dir
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self) -> dict:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self._backup_dir / f"backup_{timestamp}"
        backup_path.mkdir(parents=True, exist_ok=True)

        items = []

        # Backup memory sessions
        if SESSION_DIR.exists():
            dest = backup_path / "memory"
            shutil.copytree(SESSION_DIR, dest)
            items.append("memory/sessions")

        # Backup config snapshot
        import configs.config as config
        snapshot = {
            "version": CONFIG_VERSION,
            "timestamp": timestamp,
            "settings": {
                "model_name": config.MODEL_NAME,
                "gpu_layers": config.GPU_LAYERS,
                "whisper_model": config.WHISPER_MODEL,
                "sample_rate": config.SAMPLE_RATE,
                "wake_word": config.WAKE_WORD,
                "wake_threshold": config.WAKE_THRESHOLD,
                "wake_timeout": config.WAKE_TIMEOUT,
            },
        }
        config_path = backup_path / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
        items.append("config")

        # Backup API keys
        keys_file = Path("data/api_keys.json")
        if keys_file.exists():
            shutil.copy2(keys_file, backup_path / "api_keys.json")
            items.append("api_keys")

        return {
            "status": "backed_up",
            "backup_id": timestamp,
            "path": str(backup_path),
            "items": items,
        }

    def list_backups(self) -> list[dict]:
        backups = []
        for path in sorted(self._backup_dir.iterdir()):
            if path.is_dir() and path.name.startswith("backup_"):
                config_file = path / "config.json"
                info = {
                    "backup_id": path.name.replace("backup_", ""),
                    "path": str(path),
                }
                if config_file.exists():
                    try:
                        with open(config_file, "r", encoding="utf-8") as f:
                            snapshot = json.load(f)
                        info["config_version"] = snapshot.get("version", 0)
                        info["timestamp"] = snapshot.get("timestamp", "")
                    except Exception:
                        pass
                backups.append(info)
        return backups

    def restore_backup(self, backup_id: str) -> dict:
        backup_path = self._backup_dir / f"backup_{backup_id}"
        if not backup_path.exists():
            return {"status": "error", "error": f"Backup '{backup_id}' not found"}

        items = []

        # Restore memory sessions
        memory_backup = backup_path / "memory"
        if memory_backup.exists():
            if SESSION_DIR.exists():
                shutil.rmtree(SESSION_DIR)
            shutil.copytree(memory_backup, SESSION_DIR)
            items.append("memory/sessions")

        # Restore config
        config_file = backup_path / "config.json"
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                snapshot = json.load(f)
            settings = snapshot.get("settings", {})
            import configs.config as config
            for key, value in settings.items():
                if hasattr(config, key.upper()):
                    setattr(config, key.upper(), value)
            items.append("config")

        # Restore API keys
        keys_backup = backup_path / "api_keys.json"
        if keys_backup.exists():
            shutil.copy2(keys_backup, Path("data/api_keys.json"))
            items.append("api_keys")

        return {"status": "restored", "backup_id": backup_id, "items": items}

    def delete_backup(self, backup_id: str) -> dict:
        backup_path = self._backup_dir / f"backup_{backup_id}"
        if not backup_path.exists():
            return {"status": "error", "error": f"Backup '{backup_id}' not found"}
        shutil.rmtree(backup_path)
        return {"status": "deleted", "backup_id": backup_id}


backup_manager = BackupManager()
