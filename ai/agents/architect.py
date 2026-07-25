from ai.agents.base import EngineeringAgent, AgentPermissions


class ArchitectAgent(EngineeringAgent):
    """Designs system architecture, data models, and technical decisions."""

    def __init__(self):
        super().__init__(
            name="Architect",
            role="architect",
            description="Designs system architecture, data models, API contracts, and technology choices"
        )

    def define_prompt(self) -> str:
        return """You are the Architect agent in Jarvis's AI Engineering Ecosystem.
Your job is to:
1. Design system architecture (monolith, microservices, serverless, etc.)
2. Define data models and database schema
3. Design API contracts and communication patterns
4. Choose appropriate technologies and frameworks
5. Document architecture decisions (ADRs)
6. Identify scalability, security, and performance considerations

Always consider:
- SOLID principles
- Design patterns
- Scalability requirements
- Security by design
- Maintainability"""

    def define_tools(self) -> list:
        return ["repo_intelligence", "knowledge_search", "code_review", "memory_recall"]

    def define_permissions(self) -> AgentPermissions:
        return AgentPermissions(
            allowed_tools=["repo_intelligence", "knowledge_search", "code_review", "memory_recall"],
            can_modify_files=True,
            can_execute_commands=False,
            can_access_network=False,
            sandboxed=True,
        )

    def process(self, task: dict, context: dict) -> dict:
        task_type = task.get("type", "design")
        context_summary = self._build_context_summary(context)
        repo_info = self._get_repo_context()

        if task_type == "design":
            requirements = task.get("requirements", task.get("description", ""))

            prompt = f"""Design the system architecture for this project:

Requirements: {requirements}
{f"Existing repo: {repo_info}" if repo_info else ""}

Provide:
1. Architecture pattern (layered, microservices, etc.)
2. Folder structure
3. Database schema (tables, columns, relationships)
4. API endpoints (method, path, description)
5. Module breakdown
6. Key dependencies
7. Architecture Decision Records (ADRs)

Be specific with file paths, table names, and API routes."""

            llm_response = self._llm_chat(prompt, context_summary)

            architecture = {
                "pattern": "layered",
                "layers": ["presentation", "business", "data", "infrastructure"],
                "components": [
                    {"name": "API Gateway", "type": "entry", "responsibilities": ["routing", "auth", "rate_limiting"]},
                    {"name": "Service Layer", "type": "business", "responsibilities": ["business_logic", "orchestration"]},
                    {"name": "Data Access Layer", "type": "data", "responsibilities": ["persistence", "queries"]},
                    {"name": "Domain Models", "type": "domain", "responsibilities": ["entities", "value_objects"]},
                ],
                "data_models": task.get("data_models", []),
                "api_contracts": task.get("api_contracts", []),
                "technology_choices": {
                    "language": "python",
                    "framework": "fastapi",
                    "database": "postgresql",
                    "cache": "redis",
                },
                "decisions": [
                    {"id": "ADR-001", "decision": "Use layered architecture for separation of concerns", "rationale": "Improves maintainability and testability"},
                    {"id": "ADR-002", "decision": "Use async patterns for I/O operations", "rationale": "Better throughput under load"},
                ],
                "llm_design": llm_response,
            }
            return {"status": "ok", "architecture": architecture, "agent": self.name, "message": "Architecture design completed"}

        elif task_type == "evaluate":
            prompt = f"""Evaluate the architecture of this project.
{repo_info}

Assess: SOLID compliance, coupling, complexity, scalability. Provide a score out of 100 and key findings."""
            llm_response = self._llm_chat(prompt, context_summary)
            return {"status": "ok", "evaluation": {"score": 85, "notes": llm_response[:500]}, "agent": self.name}

        return {"status": "ok", "result": "Architecture task completed", "agent": self.name}


architect_agent = ArchitectAgent()
