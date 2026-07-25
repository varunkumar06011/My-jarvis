from pathlib import Path
from typing import Optional

from core.event_bus import bus
from ai.ecosystem.source_control import SourceControlIntegration
from ai.ecosystem.ide import IDEIntegration
from ai.ecosystem.containers import ContainerIntegration
from ai.ecosystem.build import BuildSystemIntegration
from ai.ecosystem.cicd import CICDIntegration


class DevelopmentEcosystem:
    """Unified Development Ecosystem.
    Integrates source control, IDEs, containers, build systems, and CI/CD."""

    def __init__(self, root: str = "."):
        self.root = Path(root).resolve()
        self.source_control = SourceControlIntegration()
        self.ide = IDEIntegration(root)
        self.containers = ContainerIntegration()
        self.build = BuildSystemIntegration(root)
        self.cicd = CICDIntegration(root)

    def ecosystem_status(self) -> dict:
        """Get status of all ecosystem integrations."""
        return {
            "root": str(self.root),
            "source_control": {
                "git_available": self.source_control._git_available,
            },
            "ides": self.ide.detect_ides(),
            "containers": {
                "docker_available": self.containers._docker_available,
            },
            "build_systems": self.build.detect_build_systems(),
            "cicd": self.cicd.detect_cicd(),
        }

    # ── Source Control ──

    def git_status(self, repo_path: str = ".") -> dict:
        return self.source_control.git_status(repo_path)

    def git_log(self, repo_path: str = ".", count: int = 20) -> dict:
        return self.source_control.git_log(repo_path, count)

    def pr_review(self, platform: str, repo: str, pr_number: int) -> dict:
        return self.cicd.pr_review(platform, repo, pr_number)

    def commit_analysis(self, platform: str, repo: str, sha: str) -> dict:
        return self.cicd.commit_analysis(platform, repo, sha)

    def branch_health(self, repo_path: str = ".") -> dict:
        return self.cicd.branch_health(repo_path)

    def release_summary(self, platform: str, repo: str, limit: int = 5) -> dict:
        return self.cicd.release_summary(platform, repo, limit)

    # ── IDEs ──

    def detect_ides(self) -> list:
        return self.ide.detect_ides()

    def open_in_ide(self, ide: str, file_path: str = None, line: int = None) -> dict:
        return self.ide.open(ide, file_path=file_path, line=line)

    # ── Containers ──

    def docker_status(self) -> dict:
        return self.containers.docker_status()

    def docker_build(self, dockerfile: str = "Dockerfile", tag: str = "", context: str = ".") -> dict:
        return self.containers.docker_build(dockerfile, tag, context)

    def docker_run(self, image: str, **kwargs) -> dict:
        return self.containers.docker_run(image, **kwargs)

    def docker_ps(self, all_containers: bool = False) -> dict:
        return self.containers.docker_ps(all_containers)

    def compose_up(self, cwd: str = ".", detached: bool = True, service: str = "") -> dict:
        return self.containers.compose_up(cwd=cwd, detached=detached, service=service)

    def compose_down(self, cwd: str = ".", volumes: bool = False) -> dict:
        return self.containers.compose_down(cwd=cwd, volumes=volumes)

    def analyze_dockerfile(self, dockerfile_path: str = "Dockerfile") -> dict:
        return self.containers.analyze_dockerfile(dockerfile_path)

    # ── Build ──

    def build(self, system: str = None, cwd: str = ".") -> dict:
        return self.build.build(system=system, cwd=cwd)

    def test(self, system: str = None, cwd: str = ".") -> dict:
        return self.build.test(system=system, cwd=cwd)

    def detect_build_systems(self) -> list:
        return self.build.detect_build_systems()

    # ── CI/CD ──

    def detect_cicd(self) -> list:
        return self.cicd.detect_cicd()

    def build_failures(self, platform: str, repo: str, run_id: int = None) -> dict:
        return self.cicd.build_failures(platform, repo, run_id)

    def github_workflows(self) -> dict:
        return self.cicd.github_actions_list_workflows()

    def gitlab_ci_parse(self) -> dict:
        return self.cicd.gitlab_ci_parse()

    def jenkinsfile_parse(self) -> dict:
        return self.cicd.jenkins_parse_jenkinsfile()


dev_ecosystem = DevelopmentEcosystem()
