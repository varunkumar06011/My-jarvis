import json
import os
from typing import Any

from automation.engine.context import AutomationContext
from automation.engine.rollback import RollbackManager
from automation.plugins.base import AutomationPlugin, RiskLevel


class GitHubPlugin(AutomationPlugin):
    """GitHub API integration plugin."""

    def __init__(self):
        super().__init__()
        self.name = "GitHub"
        self.description = "GitHub API: repos, issues, PRs, actions, releases"
        self.version = "1.0"
        self.author = "Jarvis"

    def _get_token(self) -> str:
        return os.getenv("GITHUB_TOKEN", "")

    def _api_call(self, method: str, endpoint: str, data: dict = None) -> dict:
        import urllib.request
        url = f"https://api.github.com{endpoint}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Jarvis-Automation",
        }
        token = self._get_token()
        if token:
            headers["Authorization"] = f"token {token}"

        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return {"error": str(e)}

    def initialize(self):
        self.register_action("github.repos", self.list_repos, RiskLevel.SAFE)
        self.register_action("github.repo_info", self.repo_info, RiskLevel.SAFE)
        self.register_action("github.issues", self.list_issues, RiskLevel.SAFE)
        self.register_action("github.create_issue", self.create_issue, RiskLevel.HIGH)
        self.register_action("github.close_issue", self.close_issue, RiskLevel.HIGH)
        self.register_action("github.pulls", self.list_pulls, RiskLevel.SAFE)
        self.register_action("github.create_pr", self.create_pr, RiskLevel.HIGH)
        self.register_action("github.merge_pr", self.merge_pr, RiskLevel.CRITICAL)
        self.register_action("github.actions", self.list_actions, RiskLevel.SAFE)
        self.register_action("github.trigger_action", self.trigger_action, RiskLevel.HIGH)
        self.register_action("github.releases", self.list_releases, RiskLevel.SAFE)
        self.register_action("github.create_release", self.create_release, RiskLevel.CRITICAL)
        self.register_action("github.user", self.get_user, RiskLevel.SAFE)
        self.register_action("github.search", self.search_repos, RiskLevel.SAFE)

        self.register_workflow({
            "id": "github_review_workflow",
            "name": "GitHub PR Review Workflow",
            "description": "List open PRs, check status, review and merge",
            "version": "1.0",
            "variables": {"repo": "owner/repo"},
            "steps": [
                {"name": "list_prs", "type": "action", "action": "github.pulls", "params": {"repo": "{{repo}}"}},
                {"name": "review_gate", "type": "approval", "approval_summary": "Review and approve PR merge"},
                {"name": "merge", "type": "action", "action": "github.merge_pr", "params": {"repo": "{{repo}}", "pr_number": 1}},
            ],
        })

    def list_repos(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        result = self._api_call("GET", "/user/repos?sort=updated&per_page=30")
        if isinstance(result, list):
            repos = [{"name": r.get("name"), "full_name": r.get("full_name"), "stars": r.get("stargazers_count"), "private": r.get("private")} for r in result]
            return {"status": "ok", "count": len(repos), "repos": repos}
        return {"status": "error", "error": result.get("error", "Unknown")}

    def repo_info(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        repo = params.get("repo", "")
        result = self._api_call("GET", f"/repos/{repo}")
        if "error" in result:
            return {"status": "error", "error": result["error"]}
        return {"status": "ok", "name": result.get("name"), "description": result.get("description"),
                "stars": result.get("stargazers_count"), "forks": result.get("forks_count"),
                "open_issues": result.get("open_issues_count"), "default_branch": result.get("default_branch")}

    def list_issues(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        repo = params.get("repo", "")
        state = params.get("state", "open")
        result = self._api_call("GET", f"/repos/{repo}/issues?state={state}&per_page=20")
        if isinstance(result, list):
            issues = [{"number": i.get("number"), "title": i.get("title"), "state": i.get("state"), "labels": [l.get("name") for l in i.get("labels", [])]} for i in result]
            return {"status": "ok", "count": len(issues), "issues": issues}
        return {"status": "error", "error": result.get("error", "Unknown")}

    def create_issue(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        repo = params.get("repo", "")
        result = self._api_call("POST", f"/repos/{repo}/issues", {
            "title": params.get("title", ""),
            "body": params.get("body", ""),
            "labels": params.get("labels", []),
        })
        if "error" in result:
            return {"status": "error", "error": result["error"]}
        return {"status": "ok", "number": result.get("number"), "url": result.get("html_url")}

    def close_issue(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        repo = params.get("repo", "")
        number = params.get("number", 0)
        result = self._api_call("PATCH", f"/repos/{repo}/issues/{number}", {"state": "closed"})
        if "error" in result:
            return {"status": "error", "error": result["error"]}
        return {"status": "ok", "number": number, "state": "closed"}

    def list_pulls(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        repo = params.get("repo", "")
        state = params.get("state", "open")
        result = self._api_call("GET", f"/repos/{repo}/pulls?state={state}&per_page=20")
        if isinstance(result, list):
            prs = [{"number": p.get("number"), "title": p.get("title"), "user": p.get("user", {}).get("login"), "draft": p.get("draft")} for p in result]
            return {"status": "ok", "count": len(prs), "pulls": prs}
        return {"status": "error", "error": result.get("error", "Unknown")}

    def create_pr(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        repo = params.get("repo", "")
        result = self._api_call("POST", f"/repos/{repo}/pulls", {
            "title": params.get("title", ""),
            "body": params.get("body", ""),
            "head": params.get("head", ""),
            "base": params.get("base", "main"),
        })
        if "error" in result:
            return {"status": "error", "error": result["error"]}
        return {"status": "ok", "number": result.get("number"), "url": result.get("html_url")}

    def merge_pr(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        repo = params.get("repo", "")
        number = params.get("pr_number", params.get("number", 0))
        result = self._api_call("PUT", f"/repos/{repo}/pulls/{number}/merge", {
            "commit_title": params.get("commit_title", f"Merge PR #{number}"),
        })
        if "error" in result:
            return {"status": "error", "error": result["error"]}
        return {"status": "ok", "merged": result.get("merged", True), "sha": result.get("sha", "")}

    def list_actions(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        repo = params.get("repo", "")
        result = self._api_call("GET", f"/repos/{repo}/actions/runs?per_page=10")
        if "error" in result:
            return {"status": "error", "error": result["error"]}
        runs = result.get("workflow_runs", [])
        actions = [{"id": r.get("id"), "name": r.get("name"), "status": r.get("status"), "conclusion": r.get("conclusion")} for r in runs]
        return {"status": "ok", "count": len(actions), "runs": actions}

    def trigger_action(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        repo = params.get("repo", "")
        workflow_id = params.get("workflow_id", "")
        ref = params.get("ref", "main")
        result = self._api_call("POST", f"/repos/{repo}/actions/workflows/{workflow_id}/dispatches", {"ref": ref})
        if "error" in result:
            return {"status": "error", "error": result["error"]}
        return {"status": "ok", "workflow_id": workflow_id, "ref": ref}

    def list_releases(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        repo = params.get("repo", "")
        result = self._api_call("GET", f"/repos/{repo}/releases?per_page=10")
        if isinstance(result, list):
            releases = [{"tag": r.get("tag_name"), "name": r.get("name"), "draft": r.get("draft"), "prerelease": r.get("prerelease")} for r in result]
            return {"status": "ok", "count": len(releases), "releases": releases}
        return {"status": "error", "error": result.get("error", "Unknown")}

    def create_release(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        repo = params.get("repo", "")
        result = self._api_call("POST", f"/repos/{repo}/releases", {
            "tag_name": params.get("tag", ""),
            "name": params.get("name", params.get("tag", "")),
            "body": params.get("body", ""),
            "draft": params.get("draft", False),
            "prerelease": params.get("prerelease", False),
        })
        if "error" in result:
            return {"status": "error", "error": result["error"]}
        return {"status": "ok", "id": result.get("id"), "url": result.get("html_url")}

    def get_user(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        result = self._api_call("GET", "/user")
        if "error" in result:
            return {"status": "error", "error": result["error"]}
        return {"status": "ok", "login": result.get("login"), "name": result.get("name"), "public_repos": result.get("public_repos")}

    def search_repos(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        query = params.get("query", "")
        result = self._api_call("GET", f"/search/repositories?q={query}&per_page=10")
        if "error" in result:
            return {"status": "error", "error": result["error"]}
        items = result.get("items", [])
        repos = [{"full_name": r.get("full_name"), "stars": r.get("stargazers_count"), "description": r.get("description", "")[:100]} for r in items]
        return {"status": "ok", "count": len(repos), "repos": repos}
