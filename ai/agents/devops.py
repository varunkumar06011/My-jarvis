from ai.agents.base import EngineeringAgent, AgentPermissions


class DevOpsEngineerAgent(EngineeringAgent):
    """Handles CI/CD, deployment, infrastructure, and containerization."""

    def __init__(self):
        super().__init__(
            name="DevOpsEngineer",
            role="devops_engineer",
            description="Handles CI/CD pipelines, deployment, infrastructure, and containerization"
        )

    def define_prompt(self) -> str:
        return """You are the DevOps Engineer agent in Jarvis's AI Engineering Ecosystem.
Your job is to:
1. Set up and maintain CI/CD pipelines
2. Configure deployment environments
3. Manage containerization (Docker, Kubernetes)
4. Configure infrastructure as code
5. Set up monitoring and alerting
6. Manage build systems and dependencies
7. Ensure zero-downtime deployments

Always:
- Follow infrastructure as code principles
- Use immutable infrastructure where possible
- Implement health checks and readiness probes
- Set up proper logging and monitoring
- Use secrets management (no hardcoded credentials)
- Implement rollback strategies"""

    def define_tools(self) -> list:
        return ["repo_intelligence", "knowledge_search", "memory_recall"]

    def define_permissions(self) -> AgentPermissions:
        return AgentPermissions(
            allowed_tools=["repo_intelligence", "knowledge_search", "memory_recall"],
            can_modify_files=True,
            can_execute_commands=True,
            can_access_network=True,
            sandboxed=False,
        )

    def process(self, task: dict, context: dict) -> dict:
        task_type = task.get("type", "deploy")
        context_summary = self._build_context_summary(context)
        repo_info = self._get_repo_context()

        if task_type == "deploy":
            environment = task.get("environment", "staging")

            prompt = f"""Set up deployment for this project:

Environment: {environment}
{f"Existing repo: {repo_info}" if repo_info else ""}

Provide:
1. Dockerfile
2. docker-compose.yml (if needed)
3. Environment configuration
4. Health check endpoints
5. Deployment strategy (rolling, blue-green, etc.)
6. Rollback plan

Write the actual configuration files, not stubs."""

            llm_response = self._llm_chat(prompt, context_summary)

            return {
                "status": "ok",
                "agent": self.name,
                "action": "deployment",
                "environment": environment,
                "strategy": "rolling",
                "config": llm_response,
                "message": f"Deployment configuration for {environment} completed",
            }

        elif task_type == "cicd":
            pipeline = task.get("pipeline", "github_actions")

            prompt = f"""Set up CI/CD pipeline for this project:

Pipeline: {pipeline}
{f"Existing repo: {repo_info}" if repo_info else ""}

Provide:
1. CI/CD configuration file (GitHub Actions YAML, etc.)
2. Build stages (install, lint, test, build, deploy)
3. Security scanning step
4. Environment secrets management
5. Deployment gates and approvals

Write the actual pipeline configuration."""

            llm_response = self._llm_chat(prompt, context_summary)

            return {
                "status": "ok",
                "agent": self.name,
                "action": "cicd_setup",
                "pipeline": pipeline,
                "stages": ["build", "test", "security_scan", "deploy"],
                "config": llm_response,
                "message": "CI/CD pipeline configured",
            }

        elif task_type == "containerize":
            prompt = f"""Containerize this project.
{f"Repo context: {repo_info}" if repo_info else ""}

Provide a complete Dockerfile and docker-compose.yml with proper multi-stage builds, health checks, and volume mappings."""
            llm_response = self._llm_chat(prompt, context_summary)

            return {
                "status": "ok",
                "agent": self.name,
                "action": "containerization",
                "dockerfile": True,
                "compose": True,
                "config": llm_response,
                "message": "Containerization completed",
            }

        return {"status": "ok", "result": "DevOps task completed", "agent": self.name}


devops_agent = DevOpsEngineerAgent()
