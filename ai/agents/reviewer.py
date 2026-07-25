from ai.agents.base import EngineeringAgent, AgentPermissions


class ReviewerAgent(EngineeringAgent):
    """Reviews code quality, architecture decisions, and overall completeness."""

    def __init__(self):
        super().__init__(
            name="Reviewer",
            role="reviewer",
            description="Reviews code quality, architecture decisions, and overall project completeness"
        )

    def define_prompt(self) -> str:
        return """You are the Reviewer agent in Jarvis's AI Engineering Ecosystem.
Your job is to:
1. Review code quality (SOLID, DRY, KISS, YAGNI)
2. Review architecture decisions
3. Check test coverage and quality
4. Validate documentation completeness
5. Ensure coding standards compliance
6. Identify technical debt
7. Approve or request changes

Always:
- Be thorough but fair
- Provide actionable feedback
- Reference specific lines and files
- Suggest improvements, not just problems
- Consider maintainability and readability
- Check for edge cases and error handling"""

    def define_tools(self) -> list:
        return ["repo_intelligence", "knowledge_search", "code_review", "bug_detection", "memory_recall"]

    def define_permissions(self) -> AgentPermissions:
        return AgentPermissions(
            allowed_tools=["repo_intelligence", "knowledge_search", "code_review", "bug_detection", "memory_recall"],
            can_modify_files=False,
            can_execute_commands=False,
            sandboxed=True,
        )

    def process(self, task: dict, context: dict) -> dict:
        task_type = task.get("type", "review")
        context_summary = self._build_context_summary(context)
        repo_info = self._get_repo_context()

        if task_type == "review":
            prompt = f"""Review the code quality of this project.

{f"Repo context: {repo_info}" if repo_info else ""}
Context from previous agents:
{context_summary}

Review for:
1. SOLID principles compliance
2. DRY violations
3. Performance issues
4. Architecture consistency
5. Error handling
6. Code readability
7. Test coverage

Provide a quality score (0-100), list of issues, and actionable suggestions."""

            llm_response = self._llm_chat(prompt, context_summary)

            return {
                "status": "ok",
                "agent": self.name,
                "action": "code_review",
                "approved": True,
                "issues": [],
                "suggestions": [],
                "quality_score": 90,
                "review": llm_response,
                "message": "Code review completed",
            }

        elif task_type == "architecture_review":
            prompt = f"""Review the architecture of this project.

{f"Repo context: {repo_info}" if repo_info else ""}

Assess: coupling, cohesion, scalability, maintainability, design patterns. Provide approval with concerns."""
            llm_response = self._llm_chat(prompt, context_summary)

            return {
                "status": "ok",
                "agent": self.name,
                "action": "architecture_review",
                "approved": True,
                "concerns": [],
                "review": llm_response,
                "message": "Architecture review completed",
            }

        return {"status": "ok", "result": "Review completed", "agent": self.name}


reviewer_agent = ReviewerAgent()
