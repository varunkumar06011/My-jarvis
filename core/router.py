import re

import ollama

from configs.config import MODEL_NAME, GPU_LAYERS
from core.tool_registry import get_tool_descriptions
from core.tool_executor import execute, extract_expression


def _ask_ai_for_tool(message: str) -> str | None:
    prompt = f"""You are a tool router. Based on the user's message, decide which tool to use.

Available tools:
{get_tool_descriptions()}

Rules:
- Respond with ONLY the tool name, or "none" if no tool applies.
- For math expressions like "2 + 3" or "10 * 5", respond "calculator".
- For questions about time, respond "time".
- For questions about date or today, respond "date".
- For questions about battery or power, respond "battery".
- For general questions, respond "none".

User message: {message}

Tool:"""

    options = {}
    if GPU_LAYERS is not None:
        options["num_gpu"] = GPU_LAYERS

    for attempt in range(3):
        try:
            response = ollama.chat(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                options=options,
            )
            result = response["message"]["content"].strip().lower()

            if result in ("none", "none.", "n/a", ""):
                return None

            first_word = result.split()[0]
            return first_word
        except Exception as e:
            error_str = str(e).lower()
            if "out-of-memory" in error_str or "failed to allocate" in error_str:
                from brain.llm import _kill_stale_llama_servers
                _kill_stale_llama_servers()
            if attempt < 2:
                import time
                time.sleep(3)
            return None


def route(message: str) -> str | None:
    calc_match = re.match(r"^[\d\s\+\-\*/\(\)\.]+$", message.strip())
    if calc_match and any(op in message for op in "+-*/"):
        return execute("calculator", message.strip())

    tool_name = _ask_ai_for_tool(message)

    if tool_name is None:
        return None

    if tool_name == "calculator":
        expr = extract_expression(message)
        if expr:
            return execute("calculator", expr)
        return None

    return execute(tool_name)
