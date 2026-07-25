import json
from pathlib import Path
from typing import Optional

from automation.engine.workflow_engine import Workflow, WorkflowStep, StepType


class TemplateManager:
    """Manages reusable workflow templates."""

    def __init__(self, templates_dir: Path = Path("automation/templates")):
        self._templates_dir = templates_dir
        self._templates_dir.mkdir(parents=True, exist_ok=True)
        self._templates: dict[str, dict] = {}
        self._load_builtin()

    def _load_builtin(self):
        builtin = {
            "open_browser_and_screenshot": {
                "id": "open_browser_and_screenshot",
                "name": "Open Browser and Screenshot",
                "description": "Open a browser, navigate to a URL, and take a screenshot",
                "version": "1.0",
                "variables": {"url": "https://example.com"},
                "steps": [
                    {"name": "open_browser", "type": "action", "action": "browser.open", "params": {"browser": "chromium"}},
                    {"name": "navigate", "type": "action", "action": "browser.navigate", "params": {"url": "{{url}}"}},
                    {"name": "screenshot", "type": "action", "action": "browser.screenshot", "params": {"name": "page_screenshot"}},
                    {"name": "close", "type": "action", "action": "browser.close"},
                ],
            },
            "file_backup": {
                "id": "file_backup",
                "name": "File Backup",
                "description": "Copy files from source to backup directory",
                "version": "1.0",
                "variables": {"src": "", "dst": ""},
                "steps": [
                    {"name": "copy_file", "type": "action", "action": "fs.copy", "params": {"src": "{{src}}", "dst": "{{dst}}"}},
                ],
            },
            "system_info": {
                "id": "system_info",
                "name": "System Information",
                "description": "Gather system information via terminal commands",
                "version": "1.0",
                "variables": {},
                "steps": [
                    {"name": "systeminfo", "type": "action", "action": "terminal.safe_execute", "params": {"command": "systeminfo", "shell": "powershell"}},
                ],
            },
            "docker_status": {
                "id": "docker_status",
                "name": "Docker Status Check",
                "description": "Check Docker container and image status",
                "version": "1.0",
                "variables": {},
                "steps": [
                    {"name": "containers", "type": "action", "action": "docker.ps", "params": {}},
                    {"name": "images", "type": "action", "action": "docker.images", "params": {}},
                    {"name": "stats", "type": "action", "action": "docker.stats", "params": {}},
                ],
            },
        }

        for tid, data in builtin.items():
            self._templates[tid] = data
            path = self._templates_dir / f"{tid}.json"
            if not path.exists():
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

    def list_templates(self) -> list[dict]:
        return [
            {
                "id": t["id"],
                "name": t["name"],
                "description": t.get("description", ""),
                "step_count": len(t.get("steps", [])),
                "version": t.get("version", "1.0"),
            }
            for t in self._templates.values()
        ]

    def get_template(self, template_id: str) -> Optional[dict]:
        return self._templates.get(template_id)

    def to_workflow(self, template_id: str, variables: Optional[dict] = None) -> Optional[Workflow]:
        data = self._templates.get(template_id)
        if data is None:
            return None
        if variables:
            data["variables"] = {**data.get("variables", {}), **variables}
        return Workflow.from_dict(data)

    def save_template(self, data: dict) -> dict:
        tid = data.get("id", "custom")
        self._templates[tid] = data
        path = self._templates_dir / f"{tid}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return {"status": "saved", "template_id": tid}

    def delete_template(self, template_id: str) -> bool:
        if template_id in self._templates:
            del self._templates[template_id]
            path = self._templates_dir / f"{template_id}.json"
            if path.exists():
                path.unlink()
            return True
        return False


template_manager = TemplateManager()
