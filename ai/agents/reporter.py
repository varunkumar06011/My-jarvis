from ai.agents.base import EngineeringAgent, AgentPermissions


class ReporterAgent(EngineeringAgent):
    """Generates reports, summaries, and documentation for stakeholders."""

    def __init__(self):
        super().__init__(
            name="Reporter",
            role="reporter",
            description="Generates reports, summaries, and documentation for stakeholders"
        )

    def define_prompt(self) -> str:
        return """You are the Reporter agent in Jarvis's AI Engineering Ecosystem.
Your job is to:
1. Generate progress reports
2. Create technical documentation
3. Summarize agent activities and outcomes
4. Create release notes
5. Generate metrics dashboards
6. Communicate status to stakeholders

Always:
- Be clear and concise
- Use appropriate technical level for audience
- Include metrics and data
- Highlight risks and blockers
- Provide actionable next steps"""

    def define_tools(self) -> list:
        return ["repo_intelligence", "knowledge_search", "memory_recall"]

    def define_permissions(self) -> AgentPermissions:
        return AgentPermissions(
            allowed_tools=["repo_intelligence", "knowledge_search", "memory_recall"],
            can_modify_files=True,
            can_execute_commands=False,
            sandboxed=True,
        )

    def process(self, task: dict, context: dict) -> dict:
        task_type = task.get("type", "report")
        context_summary = self._build_context_summary(context)

        if task_type == "report":
            report_type = task.get("report_type", "progress")

            prompt = f"""Generate a {report_type} report for this project.

Agent pipeline results:
{context_summary}

Summarize:
1. What was accomplished
2. What remains to be done
3. Risks and blockers
4. Metrics and quality scores
5. Recommended next steps

Be clear and actionable."""

            llm_response = self._llm_chat(prompt, context_summary)

            return {
                "status": "ok",
                "agent": self.name,
                "action": "report_generation",
                "report_type": report_type,
                "summary": llm_response[:500],
                "report": llm_response,
                "metrics": context.get("metrics", {}),
                "message": "Report generated",
            }

        elif task_type == "release_notes":
            version = task.get("version", "1.0.0")
            changes = task.get("changes", [])

            prompt = f"""Generate release notes for version {version}.

Changes made:
{context_summary}
{chr(10).join(changes) if changes else ""}

Format as professional release notes with:
- New features
- Bug fixes
- Breaking changes
- Migration notes
- Credits"""

            llm_response = self._llm_chat(prompt, context_summary)

            return {
                "status": "ok",
                "agent": self.name,
                "action": "release_notes",
                "version": version,
                "changes": changes,
                "notes": llm_response,
                "message": "Release notes generated",
            }

        return {"status": "ok", "result": "Report completed", "agent": self.name}


reporter_agent = ReporterAgent()
