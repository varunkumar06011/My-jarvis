import importlib
import pkgutil

import plugins


def _discover_tools():
    registry = {}

    for module_info in pkgutil.iter_modules(plugins.__path__):
        if module_info.name.startswith("_"):
            continue

        module = importlib.import_module(f"plugins.{module_info.name}")

        if hasattr(module, "TOOL") and hasattr(module, "run"):
            tool_name = module.TOOL["name"]
            registry[tool_name] = module

    return registry


TOOLS = _discover_tools()


def get_tool_descriptions():
    descriptions = []

    for tool in TOOLS.values():
        descriptions.append(f"- {tool.TOOL['name']}: {tool.TOOL['description']}")

    return "\n".join(descriptions)


def get_tool(name):
    return TOOLS.get(name)
