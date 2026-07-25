import re

from core.tool_registry import get_tool


def execute(tool_name, args=None):
    tool = get_tool(tool_name)

    if tool is None:
        return f"Tool '{tool_name}' not found."

    try:
        if args:
            return tool.run(args)
        else:
            return tool.run()
    except Exception as e:
        return f"Tool '{tool_name}' error: {e}"


def extract_expression(message):
    matches = re.findall(r"[\d\s\+\-\*/\(\)\.]+", message)
    for match in matches:
        expr = match.strip()
        if any(op in expr for op in "+-*/") and any(c.isdigit() for c in expr):
            return expr
    return None
