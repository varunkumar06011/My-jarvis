import subprocess
import json
import os
import re
from pathlib import Path
from typing import Optional
from collections import defaultdict

from core.event_bus import bus


class CICDIntegration:
    """Integrates with GitHub Actions, GitLab CI, and Jenkins for CI/CD operations."""

    def __init__(self, root: str = "."):
        self.root = Path(root).resolve()

    def detect_cicd(self) -> list:
        """Detect which CI/CD systems are configured."""
        detected = []

        github_workflows = self.root / ".github" / "workflows"
        if github_workflows.is_dir():
            yml_files = list(github_workflows.glob("*.yml")) + list(github_workflows.glob("*.yaml"))
            if yml_files:
                detected.append("github_actions")

        gitlab_ci = self.root / ".gitlab-ci.yml"
        if gitlab_ci.exists():
            detected.append("gitlab_ci")

        jenkinsfile = self.root / "Jenkinsfile"
        if jenkinsfile.exists():
            detected.append("jenkins")

        return detected

    # ── GitHub Actions ──

    def github_actions_list_workflows(self) -> dict:
        """List all GitHub Actions workflows."""
        workflows_dir = self.root / ".github" / "workflows"
        if not workflows_dir.is_dir():
            return {"status": "ok", "workflows": []}

        workflows = []
        for f in workflows_dir.glob("*.yml") + workflows_dir.glob("*.yaml"):
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                name = f.stem
                triggers = []
                jobs = []

                name_match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
                if name_match:
                    name = name_match.group(1).strip().strip('"').strip("'")

                on_match = re.search(r'^on:\s*(.+)$', content, re.MULTILINE)
                if on_match:
                    triggers.append(on_match.group(1).strip())
                elif re.search(r'^on:', content, re.MULTILINE):
                    on_block = re.search(r'^on:\s*\n((?:\s{2,}.*\n)+)', content, re.MULTILINE)
                    if on_block:
                        triggers.extend([line.strip() for line in on_block.group(1).split("\n") if line.strip()])

                job_matches = re.findall(r'^\s{2}(\w+):\s*$', content, re.MULTILINE)
                jobs = [j for j in job_matches if j not in ("steps", "runs-on", "needs", "if", "env", "with", "uses", "run", "name")]

                workflows.append({
                    "file": f.name,
                    "name": name,
                    "triggers": triggers,
                    "jobs": jobs[:10],
                })
            except Exception:
                pass

        return {"status": "ok", "workflows": workflows}

    def github_actions_get_runs(self, repo: str, limit: int = 10) -> dict:
        """Get recent GitHub Actions runs via API."""
        import urllib.request
        url = f"https://api.github.com/repos/{repo}/actions/runs?per_page={limit}"
        headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "Jarvis-Ecosystem"}
        token = os.getenv("GITHUB_TOKEN", "")
        if token:
            headers["Authorization"] = f"token {token}"

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                runs = [{
                    "id": r.get("id"),
                    "name": r.get("name"),
                    "status": r.get("status"),
                    "conclusion": r.get("conclusion"),
                    "branch": r.get("head_branch"),
                    "event": r.get("event"),
                    "created_at": r.get("created_at"),
                } for r in data.get("workflow_runs", [])]
                return {"status": "ok", "runs": runs}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def github_actions_analyze_failure(self, repo: str, run_id: int) -> dict:
        """Analyze a failed GitHub Actions run."""
        import urllib.request
        url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs"
        headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "Jarvis-Ecosystem"}
        token = os.getenv("GITHUB_TOKEN", "")
        if token:
            headers["Authorization"] = f"token {token}"

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                failed_jobs = []
                for job in data.get("jobs", []):
                    if job.get("conclusion") == "failure":
                        failed_steps = [s for s in job.get("steps", []) if s.get("conclusion") == "failure"]
                        failed_jobs.append({
                            "name": job.get("name"),
                            "status": job.get("status"),
                            "conclusion": job.get("conclusion"),
                            "failed_steps": [{
                                "name": s.get("name"),
                                "conclusion": s.get("conclusion"),
                            } for s in failed_steps],
                        })
                return {"status": "ok", "failed_jobs": failed_jobs}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── GitLab CI ──

    def gitlab_ci_parse(self) -> dict:
        """Parse .gitlab-ci.yml and extract pipeline structure."""
        ci_file = self.root / ".gitlab-ci.yml"
        if not ci_file.exists():
            return {"error": ".gitlab-ci.yml not found"}

        try:
            content = ci_file.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {"error": str(e)}

        stages = []
        jobs = []

        stages_match = re.search(r'^stages:\s*\n((?:\s+-\s+.*\n)+)', content, re.MULTILINE)
        if stages_match:
            stages = [line.strip().lstrip("- ").strip() for line in stages_match.group(1).split("\n") if line.strip()]

        job_pattern = r'^(\w[\w-]*):\s*$'
        reserved = {"stages", "variables", "include", "before_script", "after_script", "default", "image", "services", "cache", "workflow"}

        for match in re.finditer(job_pattern, content, re.MULTILINE):
            job_name = match.group(1)
            if job_name not in reserved:
                job_block_start = match.end()
                job_block = content[job_block_start:job_block_start + 500]
                stage_match = re.search(r'stage:\s*(\w+)', job_block)
                script_match = re.search(r'script:\s*\n((?:\s+-\s+.*\n)+)', job_block)

                jobs.append({
                    "name": job_name,
                    "stage": stage_match.group(1) if stage_match else "default",
                    "has_script": bool(script_match),
                })

        return {"status": "ok", "stages": stages, "jobs": jobs}

    def gitlab_ci_pipeline_status(self, project_id: int) -> dict:
        """Get GitLab CI pipeline status via API."""
        import urllib.request
        base_url = os.getenv("GITLAB_URL", "https://gitlab.com")
        url = f"{base_url}/api/v4/projects/{project_id}/pipelines?per_page=10"
        headers = {"Content-Type": "application/json"}
        token = os.getenv("GITLAB_TOKEN", "")
        if token:
            headers["PRIVATE-TOKEN"] = token

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                pipelines = json.loads(resp.read().decode())
                return {
                    "status": "ok",
                    "pipelines": [{
                        "id": p.get("id"),
                        "status": p.get("status"),
                        "ref": p.get("ref"),
                        "sha": p.get("sha", "")[:8],
                        "created_at": p.get("created_at"),
                    } for p in pipelines],
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── Jenkins ──

    def jenkins_parse_jenkinsfile(self) -> dict:
        """Parse Jenkinsfile and extract pipeline structure."""
        jenkinsfile = self.root / "Jenkinsfile"
        if not jenkinsfile.exists():
            return {"error": "Jenkinsfile not found"}

        try:
            content = jenkinsfile.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {"error": str(e)}

        stages = []
        stage_pattern = r"stage\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"
        for match in re.finditer(stage_pattern, content):
            stages.append(match.group(1))

        has_agent = bool(re.search(r"agent\s*{", content) or re.search(r"agent\s+any", content))
        has_post = bool(re.search(r"post\s*{", content))
        has_parallel = bool(re.search(r"parallel\s*{", content))

        return {
            "status": "ok",
            "stages": stages,
            "has_agent": has_agent,
            "has_post_actions": has_post,
            "has_parallel": has_parallel,
            "line_count": len(content.split("\n")),
        }

    def jenkins_build_status(self, job_url: str) -> dict:
        """Get Jenkins build status via API."""
        import urllib.request
        import base64
        url = f"{job_url}/lastBuild/api/json"
        headers = {}
        jenkins_user = os.getenv("JENKINS_USER", "")
        jenkins_token = os.getenv("JENKINS_TOKEN", "")
        if jenkins_user and jenkins_token:
            credentials = base64.b64encode(f"{jenkins_user}:{jenkins_token}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                build = json.loads(resp.read().decode())
                return {
                    "status": "ok",
                    "build_number": build.get("number"),
                    "result": build.get("result"),
                    "building": build.get("building"),
                    "duration": build.get("duration"),
                    "timestamp": build.get("timestamp"),
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── Capabilities ──

    def pr_review(self, platform: str, repo: str, pr_number: int) -> dict:
        """Review a PR on the specified platform."""
        from ai.ecosystem.source_control import source_control

        if platform == "github":
            return source_control.github_pr_review(repo, pr_number)
        elif platform == "gitlab":
            project_id = int(repo)
            return source_control.gitlab_mr_review(project_id, pr_number)
        elif platform == "bitbucket":
            parts = repo.split("/")
            if len(parts) == 2:
                return source_control.bitbucket_pr_review(parts[0], parts[1], pr_number)
            return {"error": "Bitbucket repo format: workspace/repo_slug"}
        return {"error": f"Unsupported platform: {platform}"}

    def commit_analysis(self, platform: str, repo: str, sha: str) -> dict:
        """Analyze a commit on the specified platform."""
        from ai.ecosystem.source_control import source_control

        if platform == "github":
            return source_control.github_commit_analysis(repo, sha)
        return {"error": f"Unsupported platform: {platform}"}

    def branch_health(self, repo_path: str = ".") -> dict:
        """Check branch health."""
        from ai.ecosystem.source_control import source_control
        return source_control.git_branch_health(repo_path)

    def build_failures(self, platform: str, repo: str, run_id: int = None) -> dict:
        """Analyze build failures."""
        if platform == "github":
            if run_id:
                return self.github_actions_analyze_failure(repo, run_id)
            return self.github_actions_get_runs(repo)
        elif platform == "gitlab":
            project_id = int(repo)
            return self.gitlab_ci_pipeline_status(project_id)
        elif platform == "jenkins":
            return self.jenkins_build_status(repo)
        return {"error": f"Unsupported platform: {platform}"}

    def release_summary(self, platform: str, repo: str, limit: int = 5) -> dict:
        """Get release summaries."""
        from ai.ecosystem.source_control import source_control

        if platform == "github":
            return source_control.github_release_summary(repo, limit)
        return {"error": f"Unsupported platform: {platform}"}


cicd_integration = CICDIntegration()
