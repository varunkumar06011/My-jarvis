from ai.agents.base import EngineeringAgent, AgentPermissions


class SecurityEngineerAgent(EngineeringAgent):
    """Performs security audits, vulnerability scans, and security reviews."""

    def __init__(self):
        super().__init__(
            name="SecurityEngineer",
            role="security_engineer",
            description="Performs security audits, vulnerability detection, and security reviews"
        )

    def define_prompt(self) -> str:
        return """You are the Security Engineer agent in Jarvis's AI Engineering Ecosystem.
Your job is to:
1. Perform security audits on code and infrastructure
2. Detect vulnerabilities (OWASP Top 10, CWE)
3. Review authentication and authorization
4. Check for hardcoded secrets and credentials
5. Validate input sanitization and output encoding
6. Review dependency vulnerabilities
7. Ensure compliance with security standards

Always:
- Check for injection vulnerabilities (SQL, XSS, command)
- Verify authentication mechanisms
- Check for sensitive data exposure
- Review access controls
- Identify misconfigurations
- Check dependency CVEs"""

    def define_tools(self) -> list:
        return ["repo_intelligence", "knowledge_search", "code_review", "bug_detection", "memory_recall"]

    def define_permissions(self) -> AgentPermissions:
        return AgentPermissions(
            allowed_tools=["repo_intelligence", "knowledge_search", "code_review", "bug_detection", "memory_recall"],
            can_modify_files=True,
            can_execute_commands=False,
            can_access_network=True,
            sandboxed=True,
        )

    def process(self, task: dict, context: dict) -> dict:
        task_type = task.get("type", "audit")
        context_summary = self._build_context_summary(context)
        repo_info = self._get_repo_context()

        if task_type == "audit":
            requirements = task.get("requirements", task.get("description", ""))

            prompt = f"""Perform a security audit on this project:

Requirements: {requirements}
{f"Existing repo: {repo_info}" if repo_info else ""}

Check for:
1. SQL Injection vulnerabilities
2. XSS vulnerabilities
3. Authentication/Authorization issues (JWT, sessions)
4. Hardcoded secrets and credentials
5. Input validation gaps
6. OWASP Top 10 vulnerabilities
7. Dependency CVEs
8. Permission/access control issues

Provide specific findings with severity (critical/high/medium/low), file locations, and remediation steps."""

            llm_response = self._llm_chat(prompt, context_summary)

            return {
                "status": "ok",
                "agent": self.name,
                "action": "security_audit",
                "findings": [{"severity": "info", "category": "llm_audit", "message": llm_response[:500]}],
                "risk_level": "needs_review",
                "report": llm_response,
                "message": "Security audit completed",
            }

        elif task_type == "vulnerability_scan":
            prompt = f"""Scan for vulnerabilities in this project.
{f"Repo context: {repo_info}" if repo_info else ""}

List any vulnerabilities found with severity and remediation."""
            llm_response = self._llm_chat(prompt, context_summary)

            return {
                "status": "ok",
                "agent": self.name,
                "action": "vulnerability_scan",
                "vulnerabilities": [],
                "report": llm_response,
                "message": "Vulnerability scan completed",
            }

        return {"status": "ok", "result": "Security task completed", "agent": self.name}


security_agent = SecurityEngineerAgent()
