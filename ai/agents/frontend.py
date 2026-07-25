from ai.agents.base import EngineeringAgent, AgentPermissions


class FrontendEngineerAgent(EngineeringAgent):
    """Implements frontend UI components, pages, and user interactions."""

    def __init__(self):
        super().__init__(
            name="FrontendEngineer",
            role="frontend_engineer",
            description="Implements frontend UI components, pages, state management, and user interactions"
        )

    def define_prompt(self) -> str:
        return """You are the Frontend Engineer agent in Jarvis's AI Engineering Ecosystem.
Your job is to:
1. Implement UI components following the design system
2. Create pages and routing
3. Implement state management
4. Handle user interactions and form validation
5. Ensure responsive design and accessibility
6. Optimize frontend performance

Always:
- Follow existing UI patterns and component library
- Ensure cross-browser compatibility
- Write clean, reusable components
- Handle loading and error states
- Consider accessibility (ARIA, keyboard navigation)"""

    def define_tools(self) -> list:
        return ["repo_intelligence", "knowledge_search", "code_review", "bug_detection", "code_generation", "memory_recall"]

    def define_permissions(self) -> AgentPermissions:
        return AgentPermissions(
            allowed_tools=["repo_intelligence", "knowledge_search", "code_review", "bug_detection", "code_generation", "memory_recall"],
            can_modify_files=True,
            can_execute_commands=True,
            sandboxed=False,
        )

    def process(self, task: dict, context: dict) -> dict:
        task_type = task.get("type", "implement")
        context_summary = self._build_context_summary(context)
        repo_info = self._get_repo_context()

        if task_type == "implement":
            requirements = task.get("requirements", task.get("description", ""))
            components = task.get("components", [])
            pages = task.get("pages", [])

            prompt = f"""Implement the frontend for this project:

Requirements: {requirements}
Components needed: {components}
Pages needed: {pages}
{f"Existing repo: {repo_info}" if repo_info else ""}

Generate complete, production-quality code for:
1. React/Vue/Angular components
2. Pages and layouts
3. Routing configuration
4. State management
5. Form handling and validation
6. API integration
7. Responsive design

Write the actual code, not stubs. Include imports and proper structure."""

            llm_response = self._llm_chat(prompt, context_summary)

            return {
                "status": "ok",
                "agent": self.name,
                "action": "frontend_implementation",
                "components": components,
                "pages": pages,
                "code": llm_response,
                "message": "Frontend implementation completed",
            }

        elif task_type == "fix":
            error = task.get("error", task.get("fix", ""))
            prompt = f"""Fix this frontend issue:

Error/Issue: {error}
{f"Repo context: {repo_info}" if repo_info else ""}

Provide the corrected code with explanation."""
            llm_response = self._llm_chat(prompt, context_summary)

            return {
                "status": "ok",
                "agent": self.name,
                "action": "frontend_fix",
                "fix": llm_response,
                "message": "Frontend bug fixed",
            }

        return {"status": "ok", "result": "Frontend task completed", "agent": self.name}


frontend_agent = FrontendEngineerAgent()
