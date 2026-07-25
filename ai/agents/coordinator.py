import json
import time
import uuid
from typing import Optional
from collections import defaultdict

from core.event_bus import bus
from core.metrics import metrics
from ai.agents.base import EngineeringAgent
from ai.agents.planner import PlannerAgent
from ai.agents.architect import ArchitectAgent
from ai.agents.backend import BackendEngineerAgent
from ai.agents.frontend import FrontendEngineerAgent
from ai.agents.qa import QAEngineerAgent
from ai.agents.security import SecurityEngineerAgent
from ai.agents.devops import DevOpsEngineerAgent
from ai.agents.reviewer import ReviewerAgent
from ai.agents.reporter import ReporterAgent


class AgentCoordinator:
    """Orchestrates all AI Engineering Agents in a sequential pipeline.
    Planner → Architect → Backend → Frontend → QA → Security → DevOps → Reviewer → Reporter"""

    def __init__(self):
        self.agents: dict[str, EngineeringAgent] = {}
        self._pipeline_order = [
            "Planner", "Architect", "BackendEngineer", "FrontendEngineer",
            "QAEngineer", "SecurityEngineer", "DevOpsEngineer", "Reviewer", "Reporter",
        ]
        self._sessions: dict[str, dict] = {}
        self._initialize_agents()

    def _initialize_agents(self):
        agents = [
            PlannerAgent(),
            ArchitectAgent(),
            BackendEngineerAgent(),
            FrontendEngineerAgent(),
            QAEngineerAgent(),
            SecurityEngineerAgent(),
            DevOpsEngineerAgent(),
            ReviewerAgent(),
            ReporterAgent(),
        ]

        for agent in agents:
            agent.initialize()
            self.agents[agent.name] = agent

        bus.publish("AgentsInitialized", {
            "agents": list(self.agents.keys()),
            "count": len(self.agents),
        })

    def run_pipeline(self, task: dict, context: dict = None) -> dict:
        """Run the full agent pipeline for a task."""
        session_id = uuid.uuid4().hex[:12]
        context = context or {}

        self._sessions[session_id] = {
            "id": session_id,
            "started_at": time.time(),
            "task": task,
            "results": {},
            "status": "running",
        }

        bus.publish("AgentPipelineStarted", {
            "session_id": session_id,
            "task": task.get("type", "unknown"),
        })

        pipeline_context = dict(context)
        results = {}

        for agent_name in self._pipeline_order:
            agent = self.agents.get(agent_name)
            if agent is None:
                continue

            agent_task = self._prepare_task_for_agent(agent_name, task, pipeline_context)

            result = agent.execute(agent_task, pipeline_context)
            results[agent_name] = result

            pipeline_context[agent_name] = result

            if result.get("status") == "error":
                self._sessions[session_id]["status"] = "failed"
                self._sessions[session_id]["results"] = results
                self._sessions[session_id]["error_agent"] = agent_name

                bus.publish("AgentPipelineFailed", {
                    "session_id": session_id,
                    "failed_agent": agent_name,
                    "error": result.get("error"),
                })

                return {
                    "session_id": session_id,
                    "status": "failed",
                    "failed_at": agent_name,
                    "results": results,
                    "error": result.get("error"),
                }

        self._sessions[session_id]["status"] = "completed"
        self._sessions[session_id]["completed_at"] = time.time()
        self._sessions[session_id]["results"] = results

        duration = time.time() - self._sessions[session_id]["started_at"]
        metrics.record_latency("agent_pipeline", duration * 1000)

        bus.publish("AgentPipelineCompleted", {
            "session_id": session_id,
            "duration_ms": round(duration * 1000, 2),
            "agents_run": len(results),
        })

        return {
            "session_id": session_id,
            "status": "completed",
            "duration_ms": round(duration * 1000, 2),
            "results": results,
        }

    def run_single_agent(self, agent_name: str, task: dict, context: dict = None) -> dict:
        """Run a specific agent for a task."""
        agent = self.agents.get(agent_name)
        if agent is None:
            return {"error": f"Agent '{agent_name}' not found. Available: {list(self.agents.keys())}"}

        return agent.execute(task, context or {})

    def _prepare_task_for_agent(self, agent_name: str, task: dict, context: dict) -> dict:
        """Prepare a task tailored for a specific agent in the pipeline."""
        base_task = dict(task)
        base_task["pipeline_context"] = {
            k: v for k, v in context.items()
            if k in self._pipeline_order
        }
        return base_task

    def get_agent(self, name: str) -> Optional[EngineeringAgent]:
        return self.agents.get(name)

    def list_agents(self) -> list:
        return [agent.to_dict() for agent in self.agents.values()]

    def get_agent_status(self, name: str = None) -> dict:
        if name:
            agent = self.agents.get(name)
            if agent is None:
                return {"error": f"Agent '{name}' not found"}
            return agent.get_status()
        return {name: agent.get_status() for name, agent in self.agents.items()}

    def get_session(self, session_id: str) -> Optional[dict]:
        return self._sessions.get(session_id)

    def list_sessions(self, limit: int = 20) -> list:
        sessions = sorted(self._sessions.values(), key=lambda s: s.get("started_at", 0), reverse=True)
        return [
            {
                "id": s["id"],
                "status": s["status"],
                "started_at": s["started_at"],
                "task_type": s.get("task", {}).get("type", "unknown"),
            }
            for s in sessions[:limit]
        ]

    def pipeline_status(self) -> dict:
        return {
            "pipeline_order": self._pipeline_order,
            "agent_count": len(self.agents),
            "agents": {name: agent._status for name, agent in self.agents.items()},
            "active_sessions": sum(1 for s in self._sessions.values() if s["status"] == "running"),
            "total_sessions": len(self._sessions),
        }


agent_coordinator = AgentCoordinator()
