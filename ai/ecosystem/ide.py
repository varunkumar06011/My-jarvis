import subprocess
import json
import os
from pathlib import Path
from typing import Optional

from core.event_bus import bus


class IDEIntegration:
    """Integrates with VS Code, Cursor, IntelliJ, PyCharm, and WebStorm."""

    IDE_DETECTORS = {
        "vscode": {
            "dirs": [".vscode"],
            "files": [".vscode/settings.json", ".vscode/launch.json", ".vscode/tasks.json"],
            "extensions": [".code-workspace"],
        },
        "cursor": {
            "dirs": [".cursor"],
            "files": [".cursor/settings.json"],
        },
        "intellij": {
            "dirs": [".idea"],
            "files": [".idea/workspace.xml", ".idea/modules.xml", ".idea/misc.xml"],
        },
        "pycharm": {
            "dirs": [".idea"],
            "files": [".idea/workspace.xml", ".idea/misc.xml"],
        },
        "webstorm": {
            "dirs": [".idea"],
            "files": [".idea/workspace.xml", ".idea/jsLibraryMappings.xml"],
        },
    }

    def __init__(self, root: str = "."):
        self.root = Path(root).resolve()

    def detect_ides(self) -> list:
        """Detect which IDEs are configured for this project."""
        detected = []

        for ide_name, markers in self.IDE_DETECTORS.items():
            found = False
            for d in markers.get("dirs", []):
                if (self.root / d).is_dir():
                    found = True
                    break
            if not found:
                for f in markers.get("files", []):
                    if (self.root / f).exists():
                        found = True
                        break
            if not found:
                for ext in markers.get("extensions", []):
                    if list(self.root.glob(f"*{ext}")):
                        found = True
                        break

            if found:
                detected.append(ide_name)

        return detected

    def get_vscode_config(self) -> dict:
        """Read VS Code configuration."""
        config = {}
        settings_file = self.root / ".vscode" / "settings.json"
        if settings_file.exists():
            try:
                config["settings"] = json.loads(settings_file.read_text(encoding="utf-8"))
            except Exception:
                config["settings"] = {}

        launch_file = self.root / ".vscode" / "launch.json"
        if launch_file.exists():
            try:
                config["launch"] = json.loads(launch_file.read_text(encoding="utf-8"))
            except Exception:
                config["launch"] = {}

        tasks_file = self.root / ".vscode" / "tasks.json"
        if tasks_file.exists():
            try:
                config["tasks"] = json.loads(tasks_file.read_text(encoding="utf-8"))
            except Exception:
                config["tasks"] = {}

        return config

    def get_intellij_config(self) -> dict:
        """Read IntelliJ/PyCharm/WebStorm configuration."""
        config = {}
        idea_dir = self.root / ".idea"

        if idea_dir.is_dir():
            for xml_file in idea_dir.glob("*.xml"):
                try:
                    content = xml_file.read_text(encoding="utf-8", errors="replace")
                    config[xml_file.stem] = content[:2000]
                except Exception:
                    pass

        return config

    def open_in_vscode(self, file_path: str = None, line: int = None) -> dict:
        """Open a file in VS Code."""
        cmd = ["code"]
        if file_path:
            target = str(self.root / file_path)
            if line:
                cmd.append(f"{target}:{line}")
            else:
                cmd.append(target)
        else:
            cmd.append(str(self.root))

        try:
            subprocess.run(cmd, capture_output=True, timeout=10)
            return {"status": "ok", "ide": "vscode", "command": " ".join(cmd)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def open_in_cursor(self, file_path: str = None, line: int = None) -> dict:
        """Open a file in Cursor."""
        cmd = ["cursor"]
        if file_path:
            target = str(self.root / file_path)
            if line:
                cmd.append(f"{target}:{line}")
            else:
                cmd.append(target)
        else:
            cmd.append(str(self.root))

        try:
            subprocess.run(cmd, capture_output=True, timeout=10)
            return {"status": "ok", "ide": "cursor", "command": " ".join(cmd)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def open_in_intellij(self, file_path: str = None) -> dict:
        """Open a file in IntelliJ."""
        cmd = ["idea"]
        if file_path:
            cmd.append(str(self.root / file_path))
        else:
            cmd.append(str(self.root))

        try:
            subprocess.run(cmd, capture_output=True, timeout=10)
            return {"status": "ok", "ide": "intellij", "command": " ".join(cmd)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def open_in_pycharm(self, file_path: str = None) -> dict:
        """Open a file in PyCharm."""
        cmd = ["pycharm"]
        if file_path:
            cmd.append(str(self.root / file_path))
        else:
            cmd.append(str(self.root))

        try:
            subprocess.run(cmd, capture_output=True, timeout=10)
            return {"status": "ok", "ide": "pycharm", "command": " ".join(cmd)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def open_in_webstorm(self, file_path: str = None) -> dict:
        """Open a file in WebStorm."""
        cmd = ["webstorm"]
        if file_path:
            cmd.append(str(self.root / file_path))
        else:
            cmd.append(str(self.root))

        try:
            subprocess.run(cmd, capture_output=True, timeout=10)
            return {"status": "ok", "ide": "webstorm", "command": " ".join(cmd)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def open(self, ide: str, file_path: str = None, line: int = None) -> dict:
        """Open a file in the specified IDE."""
        openers = {
            "vscode": self.open_in_vscode,
            "cursor": self.open_in_cursor,
            "intellij": self.open_in_intellij,
            "pycharm": self.open_in_pycharm,
            "webstorm": self.open_in_webstorm,
        }

        opener = openers.get(ide)
        if opener is None:
            return {"error": f"Unsupported IDE: {ide}. Supported: {list(openers.keys())}"}

        if ide in ("vscode", "cursor"):
            return opener(file_path=file_path, line=line)
        else:
            return opener(file_path=file_path)


ide_integration = IDEIntegration()
