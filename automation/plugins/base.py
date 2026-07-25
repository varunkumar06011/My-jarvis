import importlib
import inspect
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Optional

from automation.engine.workflow_engine import Workflow
from automation.policies.engine import PolicyEngine, RiskLevel, Policy


class AutomationPlugin(ABC):
    """Base class for all automation plugins.

    Each plugin registers actions, workflows, and policies
    with the automation engine on load.
    """

    RiskLevel = RiskLevel  # Expose for subclasses

    def __init__(self):
        self.name: str = ""
        self.description: str = ""
        self.version: str = "1.0"
        self.author: str = ""
        self.actions: dict[str, Callable] = {}
        self.workflows: list[dict] = []
        self.policies: dict[str, Policy] = {}

    @abstractmethod
    def initialize(self) -> None:
        """Register actions, workflows, and policies."""
        ...

    def register_action(self, action: str, handler: Callable, risk: RiskLevel = RiskLevel.SAFE,
                         timeout: float = 300, max_retries: int = 2, requires_rollback: bool = False):
        self.actions[action] = handler
        self.policies[action] = Policy(
            action=action,
            risk=risk,
            timeout=timeout,
            max_retries=max_retries,
            requires_rollback=requires_rollback,
            requires_approval=risk in (RiskLevel.HIGH, RiskLevel.CRITICAL),
            allowed_in_sandbox=risk != RiskLevel.CRITICAL,
        )

    def register_workflow(self, workflow: dict):
        self.workflows.append(workflow)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "actions": list(self.actions.keys()),
            "workflows": [w.get("id", w.get("name", "")) for w in self.workflows],
            "policy_count": len(self.policies),
        }


class PluginLoader:
    """Discovers and loads automation plugins from the plugins directory."""

    def __init__(self, plugins_dir: Path = Path("automation/plugins")):
        self._plugins_dir = plugins_dir
        self._loaded: dict[str, AutomationPlugin] = {}

    def discover(self) -> list[str]:
        """Find all plugin directories with a plugin.py file."""
        discovered = []
        if not self._plugins_dir.exists():
            return discovered

        for item in self._plugins_dir.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                plugin_file = item / "plugin.py"
                if plugin_file.exists():
                    discovered.append(item.name)
        return discovered

    def load_plugin(self, plugin_name: str) -> Optional[AutomationPlugin]:
        """Load a single plugin by directory name."""
        try:
            module = importlib.import_module(f"automation.plugins.{plugin_name}.plugin")
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and issubclass(obj, AutomationPlugin)
                        and obj is not AutomationPlugin):
                    plugin = obj()
                    plugin.initialize()
                    self._loaded[plugin_name] = plugin
                    return plugin
        except Exception as e:
            print(f"[Plugins] Failed to load '{plugin_name}': {e}")
        return None

    def load_all(self) -> list[str]:
        """Discover and load all plugins. Returns list of loaded plugin names."""
        discovered = self.discover()
        loaded = []
        for name in discovered:
            plugin = self.load_plugin(name)
            if plugin:
                loaded.append(name)
                print(f"[Plugins] Loaded: {plugin.name} v{plugin.version} ({len(plugin.actions)} actions)")
        return loaded

    def get_plugin(self, name: str) -> Optional[AutomationPlugin]:
        return self._loaded.get(name)

    def list_plugins(self) -> list[dict]:
        return [p.to_dict() for p in self._loaded.values()]

    def get_all_actions(self) -> dict[str, Callable]:
        actions = {}
        for plugin in self._loaded.values():
            actions.update(plugin.actions)
        return actions

    def get_all_policies(self) -> dict[str, Policy]:
        policies = {}
        for plugin in self._loaded.values():
            policies.update(plugin.policies)
        return policies

    def get_all_workflows(self) -> list[dict]:
        workflows = []
        for plugin in self._loaded.values():
            workflows.extend(plugin.workflows)
        return workflows


plugin_loader = PluginLoader()
