from ai.agents.base import EngineeringAgent, AgentPermissions


class BackendEngineerAgent(EngineeringAgent):
    """Implements backend services, APIs, data models, and business logic."""

    def __init__(self):
        super().__init__(
            name="BackendEngineer",
            role="backend_engineer",
            description="Implements backend services, APIs, data models, and business logic"
        )

    def define_prompt(self) -> str:
        return """You are the Backend Engineer agent in Jarvis's AI Engineering Ecosystem.
Your job is to:
1. Implement backend services and business logic
2. Create API endpoints following the architecture design
3. Implement data models and database access
4. Write clean, testable, well-structured code
5. Handle errors, validation, and edge cases
6. Follow SOLID, DRY, and KISS principles

Always:
- Write production-quality code
- Include proper error handling
- Add type hints
- Follow existing code patterns in the repository
- Consider performance and security"""

    def define_tools(self) -> list:
        return ["repo_intelligence", "knowledge_search", "code_review", "bug_detection", "code_generation", "memory_recall"]

    def define_permissions(self) -> AgentPermissions:
        return AgentPermissions(
            allowed_tools=["repo_intelligence", "knowledge_search", "code_review", "bug_detection", "code_generation", "memory_recall"],
            can_modify_files=True,
            can_execute_commands=True,
            can_access_database=True,
            sandboxed=False,
        )

    def process(self, task: dict, context: dict) -> dict:
        task_type = task.get("type", "implement")
        context_summary = self._build_context_summary(context)
        repo_info = self._get_repo_context()

        if task_type == "implement":
            requirements = task.get("requirements", task.get("description", ""))
            components = task.get("components", task.get("services", []))

            prompt = f"""Implement the backend for this project:

Requirements: {requirements}
Components needed: {components}
{f"Existing repo: {repo_info}" if repo_info else ""}

Generate complete, production-quality code for:
1. Controllers/Route handlers
2. Service layer (business logic)
3. Data access / repository layer
4. Middleware
5. Data models / schemas
6. Error handling

Include proper imports, type hints, and error handling. Write the actual code, not stubs."""

            llm_response = self._llm_chat(prompt, context_summary)

            return {
                "status": "ok",
                "agent": self.name,
                "action": "implementation",
                "files_created": task.get("files", []),
                "services": task.get("services", []),
                "endpoints": task.get("endpoints", []),
                "code": llm_response,
                "message": "Backend implementation completed",
            }

        elif task_type == "fix":
            error = task.get("error", task.get("fix", ""))
            prompt = f"""Fix this backend issue:

Error/Issue: {error}
{f"Repo context: {repo_info}" if repo_info else ""}

Provide the corrected code with explanation of what was wrong and how it was fixed."""
            llm_response = self._llm_chat(prompt, context_summary)

            return {
                "status": "ok",
                "agent": self.name,
                "action": "bug_fix",
                "fix": llm_response,
                "message": "Backend bug fixed",
            }

        return {"status": "ok", "result": "Backend task completed", "agent": self.name}


backend_agent = BackendEngineerAgent()
