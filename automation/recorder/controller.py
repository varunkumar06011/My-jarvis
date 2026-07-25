import json
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from automation.engine.context import AutomationContext
from automation.engine.rollback import RollbackManager


class MacroRecorder:
    """Record and replay user actions: mouse, keyboard, windows, browser."""

    def __init__(self, macros_dir: Path = Path("data/macros")):
        self._macros_dir = macros_dir
        self._macros_dir.mkdir(parents=True, exist_ok=True)
        self._recording: list[dict] = []
        self._is_recording = False
        self._start_time = 0

    def start_recording(self):
        self._recording = []
        self._is_recording = True
        self._start_time = time.time()

    def stop_recording(self) -> list[dict]:
        self._is_recording = False
        return list(self._recording)

    def record_action(self, action_type: str, data: dict):
        if not self._is_recording:
            return
        self._recording.append({
            "type": action_type,
            "data": data,
            "timestamp": time.time() - self._start_time,
        })

    def save_macro(self, name: str, description: str = "") -> dict:
        macro_id = uuid.uuid4().hex[:8]
        macro = {
            "id": macro_id,
            "name": name,
            "description": description,
            "actions": self._recording,
            "created_at": time.time(),
        }
        path = self._macros_dir / f"{macro_id}_{name.replace(' ', '_')}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(macro, f, indent=2, ensure_ascii=False)
        return {"status": "saved", "macro_id": macro_id, "path": str(path), "actions": len(self._recording)}

    def load_macro(self, macro_id: str) -> Optional[dict]:
        for path in self._macros_dir.glob("*.json"):
            with open(path, "r", encoding="utf-8") as f:
                macro = json.load(f)
                if macro.get("id") == macro_id:
                    return macro
        return None

    def list_macros(self) -> list[dict]:
        macros = []
        for path in self._macros_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    macro = json.load(f)
                    macros.append({
                        "id": macro["id"],
                        "name": macro["name"],
                        "description": macro.get("description", ""),
                        "actions": len(macro.get("actions", [])),
                        "created_at": macro.get("created_at", 0),
                    })
            except Exception:
                continue
        return macros

    def replay(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        macro_id = params.get("macro_id", "")
        speed = params.get("speed", "normal")  # normal, fast, step
        macro = self.load_macro(macro_id)
        if macro is None:
            return {"status": "error", "error": f"Macro '{macro_id}' not found"}

        actions = macro.get("actions", [])
        speed_multiplier = 0.1 if speed == "fast" else 1.0 if speed == "normal" else 2.0

        results = []
        prev_timestamp = 0
        for action in actions:
            delay = (action["timestamp"] - prev_timestamp) * speed_multiplier
            if delay > 0:
                time.sleep(min(delay, 10))

            result = self._execute_action(action, ctx)
            results.append(result)
            prev_timestamp = action["timestamp"]

        return {"status": "ok", "macro_id": macro_id, "actions_executed": len(results)}

    def _execute_action(self, action: dict, ctx: AutomationContext) -> dict:
        action_type = action.get("type", "")
        data = action.get("data", {})

        if action_type == "mouse_click":
            try:
                import pyautogui
                pyautogui.click(data.get("x", 0), data.get("y", 0))
                return {"status": "ok", "type": "mouse_click"}
            except ImportError:
                return {"status": "error", "error": "pyautogui not installed"}

        elif action_type == "mouse_move":
            try:
                import pyautogui
                pyautogui.moveTo(data.get("x", 0), data.get("y", 0))
                return {"status": "ok", "type": "mouse_move"}
            except ImportError:
                return {"status": "error", "error": "pyautogui not installed"}

        elif action_type == "key_press":
            try:
                import pyautogui
                pyautogui.press(data.get("key", ""))
                return {"status": "ok", "type": "key_press"}
            except ImportError:
                return {"status": "error", "error": "pyautogui not installed"}

        elif action_type == "key_type":
            try:
                import pyautogui
                pyautogui.typewrite(data.get("text", ""))
                return {"status": "ok", "type": "key_type"}
            except ImportError:
                return {"status": "error", "error": "pyautogui not installed"}

        return {"status": "skipped", "type": action_type}

    def delete_macro(self, macro_id: str) -> bool:
        for path in self._macros_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    macro = json.load(f)
                    if macro.get("id") == macro_id:
                        path.unlink()
                        return True
            except Exception:
                continue
        return False


macro_recorder = MacroRecorder()
