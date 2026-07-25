import json
import threading
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

PREFERENCES_FILE = Path("data/preferences.json")


class UserPreferences:
    def __init__(self):
        self._prefs: dict[str, any] = {}
        self._coding_style: dict[str, any] = {}
        self._naming_conventions: dict[str, str] = {}
        self._frequent_workflows: dict[str, int] = defaultdict(int)
        self._common_fixes: list[dict] = []
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if PREFERENCES_FILE.exists():
            try:
                data = json.loads(PREFERENCES_FILE.read_text(encoding="utf-8"))
                self._prefs = data.get("prefs", {})
                self._coding_style = data.get("coding_style", {})
                self._naming_conventions = data.get("naming_conventions", {})
                self._frequent_workflows = defaultdict(int, data.get("frequent_workflows", {}))
                self._common_fixes = data.get("common_fixes", [])
            except Exception:
                pass

    def _save(self):
        with self._lock:
            data = {
                "prefs": self._prefs,
                "coding_style": self._coding_style,
                "naming_conventions": self._naming_conventions,
                "frequent_workflows": dict(self._frequent_workflows),
                "common_fixes": self._common_fixes,
            }
        PREFERENCES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def set(self, key: str, value):
        with self._lock:
            self._prefs[key] = value
        self._save()

    def get(self, key: str, default=None):
        with self._lock:
            return self._prefs.get(key, default)

    def set_coding_style(self, key: str, value: str):
        with self._lock:
            self._coding_style[key] = value
        self._save()

    def get_coding_style(self) -> dict:
        with self._lock:
            return dict(self._coding_style)

    def set_naming_convention(self, context: str, convention: str):
        with self._lock:
            self._naming_conventions[context] = convention
        self._save()

    def get_naming_conventions(self) -> dict:
        with self._lock:
            return dict(self._naming_conventions)

    def record_workflow(self, workflow_name: str):
        with self._lock:
            self._frequent_workflows[workflow_name] += 1
        self._save()

    def get_frequent_workflows(self, limit: int = 10) -> list[dict]:
        with self._lock:
            workflows = sorted(self._frequent_workflows.items(), key=lambda x: -x[1])
        return [{"name": name, "count": count} for name, count in workflows[:limit]]

    def record_fix(self, problem: str, solution: str, context: str = ""):
        with self._lock:
            self._common_fixes.append({
                "problem": problem,
                "solution": solution,
                "context": context,
                "timestamp": datetime.now().isoformat(),
            })
            if len(self._common_fixes) > 500:
                self._common_fixes = self._common_fixes[-500:]
        self._save()

    def search_fixes(self, query: str, limit: int = 10) -> list[dict]:
        query_lower = query.lower()
        with self._lock:
            fixes = list(self._common_fixes)

        results = []
        for fix in reversed(fixes):
            if query_lower in fix.get("problem", "").lower() or query_lower in fix.get("solution", "").lower():
                results.append(fix)
                if len(results) >= limit:
                    break
        return results

    def stats(self) -> dict:
        with self._lock:
            return {
                "total_prefs": len(self._prefs),
                "coding_style_rules": len(self._coding_style),
                "naming_conventions": len(self._naming_conventions),
                "workflow_types": len(self._frequent_workflows),
                "recorded_fixes": len(self._common_fixes),
                "top_workflows": self.get_frequent_workflows(5),
            }


user_preferences = UserPreferences()
