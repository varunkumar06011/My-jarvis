import json
import time
import threading
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Any, Callable
from collections import defaultdict

import ollama

from core.event_bus import bus
from core.metrics import metrics
from configs.config import MODEL_NAME, GPU_LAYERS


class AgentMemory:
    """Per-agent memory store for conversations, decisions, and context."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self._entries: list[dict] = []
        self._lock = threading.Lock()

    def store(self, entry_type: str, content: str, metadata: dict = None) -> dict:
        entry = {
            "id": uuid.uuid4().hex[:12],
            "agent": self.agent_name,
            "type": entry_type,
            "content": content,
            "metadata": metadata or {},
            "timestamp": time.time(),
        }
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > 500:
                self._entries = self._entries[-500:]
        return entry

    def recall(self, query: str = None, entry_type: str = None, limit: int = 20) -> list:
        with self._lock:
            entries = list(self._entries)

        results = []
        query_lower = query.lower() if query else ""

        for entry in reversed(entries):
            if entry_type and entry["type"] != entry_type:
                continue
            if query_lower and query_lower not in entry["content"].lower():
                continue
            results.append(entry)
            if len(results) >= limit:
                break

        return results

    def clear(self):
        with self._lock:
            self._entries.clear()

    def count(self) -> int:
        with self._lock:
            return len(self._entries)


class AgentMetrics:
    """Per-agent metrics tracking."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self._counters: dict[str, float] = defaultdict(float)
        self._timers: dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()

    def increment(self, name: str, value: float = 1):
        with self._lock:
            self._counters[name] += value
        metrics.increment(f"agent.{self.agent_name}.{name}", value)

    def record_time(self, name: str, duration_ms: float):
        with self._lock:
            self._timers[name].append(duration_ms)
            if len(self._timers[name]) > 100:
                self._timers[name] = self._timers[name][-100:]
        metrics.record_latency(f"agent.{self.agent_name}.{name}", duration_ms)

    def snapshot(self) -> dict:
        with self._lock:
            counters = dict(self._counters)
            timers = {}
            for name, values in self._timers.items():
                if values:
                    timers[name] = {
                        "count": len(values),
                        "avg_ms": round(sum(values) / len(values), 2),
                        "min_ms": round(min(values), 2),
                        "max_ms": round(max(values), 2),
                    }
        return {"counters": counters, "timers": timers}


class AgentPermissions:
    """Defines what an agent is allowed to do."""

    def __init__(self, allowed_tools: list = None, allowed_actions: list = None,
                 can_modify_files: bool = False, can_execute_commands: bool = False,
                 can_access_network: bool = False, can_access_database: bool = False,
                 max_file_size_mb: int = 10, sandboxed: bool = True):
        self.allowed_tools = allowed_tools or []
        self.allowed_actions = allowed_actions or []
        self.can_modify_files = can_modify_files
        self.can_execute_commands = can_execute_commands
        self.can_access_network = can_access_network
        self.can_access_database = can_access_database
        self.max_file_size_mb = max_file_size_mb
        self.sandboxed = sandboxed

    def can_use_tool(self, tool_name: str) -> bool:
        if not self.allowed_tools:
            return True
        return tool_name in self.allowed_tools

    def can_perform_action(self, action: str) -> bool:
        if not self.allowed_actions:
            return True
        return action in self.allowed_actions

    def to_dict(self) -> dict:
        return {
            "allowed_tools": self.allowed_tools,
            "allowed_actions": self.allowed_actions,
            "can_modify_files": self.can_modify_files,
            "can_execute_commands": self.can_execute_commands,
            "can_access_network": self.can_access_network,
            "can_access_database": self.can_access_database,
            "max_file_size_mb": self.max_file_size_mb,
            "sandboxed": self.sandboxed,
        }


class EngineeringAgent(ABC):
    """Base class for all AI Engineering Agents.
    Each agent has its own prompt, tools, permissions, memory, and metrics."""

    def __init__(self, name: str, role: str, description: str = ""):
        self.name = name
        self.role = role
        self.description = description
        self.system_prompt = ""
        self.tools: list[str] = []
        self.permissions = AgentPermissions()
        self.memory = AgentMemory(name)
        self.metrics = AgentMetrics(name)
        self._status = "idle"
        self._current_task: Optional[dict] = None

    @abstractmethod
    def define_prompt(self) -> str:
        """Return the system prompt for this agent."""
        ...

    @abstractmethod
    def define_tools(self) -> list[str]:
        """Return the list of tool names this agent can use."""
        ...

    @abstractmethod
    def define_permissions(self) -> AgentPermissions:
        """Return the permissions for this agent."""
        ...

    def initialize(self):
        """Initialize the agent's prompt, tools, and permissions."""
        self.system_prompt = self.define_prompt()
        self.tools = self.define_tools()
        self.permissions = self.define_permissions()

    def execute(self, task: dict, context: dict = None) -> dict:
        """Execute a task. Override in subclasses for specific behavior."""
        self._status = "running"
        self._current_task = task
        self.metrics.increment("tasks_started")

        bus.publish("AgentTaskStarted", {
            "agent": self.name,
            "task": task.get("type", "unknown"),
        })

        start_time = time.time()

        try:
            result = self.process(task, context or {})
            self._status = "completed"
            self.metrics.increment("tasks_completed")

            self.memory.store("task_result", json.dumps(result, default=str), {
                "task_type": task.get("type"),
                "success": result.get("status") == "ok",
            })

            bus.publish("AgentTaskCompleted", {
                "agent": self.name,
                "task": task.get("type"),
                "success": result.get("status") == "ok",
            })

            return result

        except Exception as e:
            self._status = "failed"
            self.metrics.increment("tasks_failed")
            self.memory.store("error", str(e), {"task_type": task.get("type")})

            bus.publish("AgentTaskFailed", {
                "agent": self.name,
                "task": task.get("type"),
                "error": str(e),
            })

            return {"status": "error", "error": str(e), "agent": self.name}

        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.metrics.record_time("task_execution", duration_ms)
            self._current_task = None

    @abstractmethod
    def process(self, task: dict, context: dict) -> dict:
        """Process a task. Must be implemented by each agent."""
        ...

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "status": self._status,
            "current_task": self._current_task,
            "memory_count": self.memory.count(),
            "metrics": self.metrics.snapshot(),
            "permissions": self.permissions.to_dict(),
        }

    def _llm_chat(self, user_message: str, context_summary: str = "") -> str:
        """Send a message to the LLM using this agent's system prompt.
        Returns the LLM's response text."""
        messages = [{"role": "system", "content": self.system_prompt}]

        if context_summary:
            messages.append({"role": "system", "content": f"Context from previous agents:\n{context_summary}"})

        messages.append({"role": "user", "content": user_message})

        options = {}
        if GPU_LAYERS is not None:
            options["num_gpu"] = GPU_LAYERS

        for attempt in range(3):
            try:
                response = ollama.chat(
                    model=MODEL_NAME,
                    messages=messages,
                    options=options,
                )
                reply = response["message"]["content"]
                self.memory.store("llm_response", reply[:500], {"attempt": attempt})
                return reply
            except Exception as e:
                error_str = str(e).lower()
                if "out-of-memory" in error_str or "failed to allocate" in error_str:
                    from brain.llm import _kill_stale_llama_servers
                    _kill_stale_llama_servers()
                if attempt < 2:
                    time.sleep(3)
                else:
                    self.memory.store("error", str(e), {"phase": "llm_chat"})
                    return f"[LLM Error: {e}]"

    def _build_context_summary(self, context: dict) -> str:
        """Build a text summary of results from previous agents in the pipeline."""
        parts = []
        for agent_name, result in context.items():
            if isinstance(result, dict) and agent_name in (
                "Planner", "Architect", "BackendEngineer", "FrontendEngineer",
                "QAEngineer", "SecurityEngineer", "DevOpsEngineer", "Reviewer",
            ):
                summary = result.get("message", result.get("summary", ""))
                if summary:
                    parts.append(f"[{agent_name}]: {summary}")
        return "\n".join(parts) if parts else ""

    def _get_repo_context(self) -> str:
        """Get repository intelligence summary if available."""
        try:
            from core.service_registry import registry
            if registry.has("repo_intelligence"):
                ri = registry.get("repo_intelligence")
                summary = ri.get_summary()
                return (
                    f"Project: {summary.get('root', 'unknown')}, "
                    f"Language: {summary.get('primary_language', 'unknown')}, "
                    f"Framework: {summary.get('primary_framework', 'unknown')}, "
                    f"Modules: {summary.get('module_count', 0)}, "
                    f"Symbols: {summary.get('symbol_count', 0)}, "
                    f"APIs: {summary.get('api_count', 0)}"
                )
        except Exception:
            pass
        return ""

    def _search_knowledge(self, query: str, limit: int = 5) -> str:
        """Search the knowledge engine for relevant context."""
        try:
            from core.service_registry import registry
            if registry.has("knowledge_engine"):
                ke = registry.get("knowledge_engine")
                results = ke.search(query, limit=limit)
                if results:
                    parts = []
                    for r in results[:limit]:
                        content = r.get("content", r.get("text", ""))[:200]
                        parts.append(content)
                    return "\n".join(parts)
        except Exception:
            pass
        return ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "tools": self.tools,
            "permissions": self.permissions.to_dict(),
            "status": self._status,
        }
