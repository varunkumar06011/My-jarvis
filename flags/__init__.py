import json
import threading
from pathlib import Path
from typing import Optional

FLAGS_DIR = Path("flags")
FLAGS_FILE = FLAGS_DIR / "flags.json"

DEFAULT_FLAGS = {
    "browser_v1": False,
    "github_v1": False,
    "automation_v1": False,
    "agents_v1": False,
    "vision_beta": False,
    "event_store": True,
    "metrics": True,
    "telemetry": True,
    "recovery_engine": True,
    "performance_dashboard": True,
    "diagnostics_api": True,
}


class FeatureFlagManager:
    def __init__(self, flags_file: Path = FLAGS_FILE):
        self._flags_file = flags_file
        self._flags: dict[str, bool] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        FLAGS_DIR.mkdir(parents=True, exist_ok=True)

        if self._flags_file.exists():
            try:
                with open(self._flags_file, "r", encoding="utf-8") as f:
                    self._flags = json.load(f)
            except Exception:
                self._flags = dict(DEFAULT_FLAGS)
        else:
            self._flags = dict(DEFAULT_FLAGS)
            self._save()

        # Merge any new default flags that aren't in the file
        for key, default_val in DEFAULT_FLAGS.items():
            if key not in self._flags:
                self._flags[key] = default_val

        self._save()

    def _save(self):
        try:
            with open(self._flags_file, "w", encoding="utf-8") as f:
                json.dump(self._flags, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def is_enabled(self, name: str) -> bool:
        with self._lock:
            return self._flags.get(name, False)

    def enable(self, name: str):
        with self._lock:
            self._flags[name] = True
            self._save()

    def disable(self, name: str):
        with self._lock:
            self._flags[name] = False
            self._save()

    def set(self, name: str, enabled: bool):
        with self._lock:
            self._flags[name] = enabled
            self._save()

    def list_flags(self) -> dict[str, bool]:
        with self._lock:
            return dict(self._flags)

    def reset_defaults(self):
        with self._lock:
            self._flags = dict(DEFAULT_FLAGS)
            self._save()


flag_manager = FeatureFlagManager()
