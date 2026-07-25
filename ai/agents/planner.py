from ai.agents.base import EngineeringAgent, AgentPermissions


class PlannerAgent(EngineeringAgent):
    """Plans project tasks, breaks down requirements, creates roadmaps."""

    def __init__(self):
        super().__init__(
            name="Planner",
            role="planner",
            description="Breaks down requirements into actionable tasks and milestones"
        )

    def define_prompt(self) -> str:
        return """You are the Planner agent in Jarvis's AI Engineering Ecosystem.
Your job is to:
1. Analyze requirements and break them into actionable tasks
2. Create milestones with clear completion criteria
3. Estimate effort and identify dependencies
4. Prioritize tasks based on impact and risk
5. Create a roadmap that other agents can follow

Always output structured plans with:
- Task ID, name, description
- Dependencies (which tasks must complete first)
- Estimated effort (small/medium/large)
- Priority (critical/high/medium/low)
- Completion criteria
- Assigned agent (Architect, Backend, Frontend, QA, Security, DevOps)"""

    def define_tools(self) -> list:
        return ["repo_intelligence", "knowledge_search", "memory_recall"]

    def define_permissions(self) -> AgentPermissions:
        return AgentPermissions(
            allowed_tools=["repo_intelligence", "knowledge_search", "memory_recall"],
            can_modify_files=False,
            can_execute_commands=False,
            can_access_network=False,
            sandboxed=True,
        )

    def process(self, task: dict, context: dict) -> dict:
        requirements = task.get("requirements", task.get("description", task.get("task", "")))
        project_type = task.get("project_type", "unknown")

        context_summary = self._build_context_summary(context)
        repo_info = self._get_repo_context()

        prompt = f"""Plan the following software project. Break it down into actionable milestones and tasks.

Project: {requirements}
Type: {project_type}

{f"Existing repository context: {repo_info}" if repo_info else ""}

Provide a structured plan with milestones, each containing tasks with:
- Task ID, name, description
- Assigned agent (Architect, Backend, Frontend, QA, Security, DevOps)
- Effort estimate (small/medium/large)
- Priority (critical/high/medium/low)
- Dependencies

Format as a clear structured list."""

        llm_response = self._llm_chat(prompt, context_summary)

        plan = {
            "milestones": [
                {
                    "id": "M1",
                    "name": "Architecture Design",
                    "tasks": [
                        {"id": "T1", "name": "Define system architecture", "agent": "Architect", "effort": "medium", "priority": "critical", "depends_on": []},
                        {"id": "T2", "name": "Define data models", "agent": "Architect", "effort": "medium", "priority": "high", "depends_on": ["T1"]},
                    ],
                },
                {
                    "id": "M2",
                    "name": "Backend Implementation",
                    "tasks": [
                        {"id": "T3", "name": "Implement core services", "agent": "Backend", "effort": "large", "priority": "critical", "depends_on": ["T2"]},
                        {"id": "T4", "name": "Implement API endpoints", "agent": "Backend", "effort": "medium", "priority": "high", "depends_on": ["T3"]},
                    ],
                },
                {
                    "id": "M3",
                    "name": "Frontend Implementation",
                    "tasks": [
                        {"id": "T5", "name": "Build UI components", "agent": "Frontend", "effort": "large", "priority": "high", "depends_on": ["T4"]},
                    ],
                },
                {
                    "id": "M4",
                    "name": "Quality & Security",
                    "tasks": [
                        {"id": "T6", "name": "Write tests", "agent": "QA", "effort": "medium", "priority": "high", "depends_on": ["T3", "T5"]},
                        {"id": "T7", "name": "Security audit", "agent": "Security", "effort": "medium", "priority": "critical", "depends_on": ["T4"]},
                    ],
                },
                {
                    "id": "M5",
                    "name": "Deployment",
                    "tasks": [
                        {"id": "T8", "name": "Set up CI/CD", "agent": "DevOps", "effort": "medium", "priority": "high", "depends_on": ["T6", "T7"]},
                        {"id": "T9", "name": "Deploy to production", "agent": "DevOps", "effort": "small", "priority": "critical", "depends_on": ["T8"]},
                    ],
                },
            ],
            "requirements": requirements,
            "project_type": project_type,
            "total_tasks": 9,
            "estimated_effort": "large",
            "llm_plan": llm_response,
        }

        return {"status": "ok", "plan": plan, "agent": self.name, "message": f"Project plan created for: {requirements}"}


planner_agent = PlannerAgent()
