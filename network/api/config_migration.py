import json
from pathlib import Path

from configs.config import CONFIG_VERSION

CONFIG_SNAPSHOT = Path("data/config_snapshot.json")


def save_config_snapshot():
    """Save current config values to a snapshot file for migration tracking."""
    import configs.config as config

    snapshot = {
        "version": CONFIG_VERSION,
        "settings": {
            "model_name": config.MODEL_NAME,
            "gpu_layers": config.GPU_LAYERS,
            "llm_max_retries": config.LLM_MAX_RETRIES,
            "llm_retry_delay": config.LLM_RETRY_DELAY,
            "app_name": config.APP_NAME,
            "version": config.VERSION,
            "whisper_model": config.WHISPER_MODEL,
            "sample_rate": config.SAMPLE_RATE,
            "silence_timeout": config.SILENCE_TIMEOUT,
            "max_record_seconds": config.MAX_RECORD_SECONDS,
            "wake_word": config.WAKE_WORD,
            "wake_threshold": config.WAKE_THRESHOLD,
            "wake_timeout": config.WAKE_TIMEOUT,
            "api_host": config.API_HOST,
            "api_port": config.API_PORT,
            "api_rate_limit_per_minute": config.API_RATE_LIMIT_PER_MINUTE,
            "api_rate_limit_per_hour": config.API_RATE_LIMIT_PER_HOUR,
            "api_jwt_expire_seconds": config.API_JWT_EXPIRE_SECONDS,
            "api_enable_docs": config.API_ENABLE_DOCS,
        },
    }

    CONFIG_SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_SNAPSHOT, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    return snapshot


def load_config_snapshot() -> dict | None:
    if not CONFIG_SNAPSHOT.exists():
        return None
    try:
        with open(CONFIG_SNAPSHOT, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def migrate_config() -> dict:
    """Check for config snapshots from older versions and migrate if needed."""
    snapshot = load_config_snapshot()

    if snapshot is None:
        # First run — save current config
        saved = save_config_snapshot()
        return {"status": "created", "version": CONFIG_VERSION, "snapshot": saved}

    old_version = snapshot.get("version", 0)

    if old_version < CONFIG_VERSION:
        # Run migrations
        migrations_applied = []

        # Future: add migration logic here per version bump
        # e.g., if old_version < 2: rename old keys, etc.

        save_config_snapshot()
        return {
            "status": "migrated",
            "from_version": old_version,
            "to_version": CONFIG_VERSION,
            "migrations": migrations_applied,
        }

    return {"status": "current", "version": CONFIG_VERSION}
