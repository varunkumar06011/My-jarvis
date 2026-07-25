import subprocess
import json
import os
from typing import Optional
from pathlib import Path

from core.event_bus import bus


class SourceControlIntegration:
    """Integrates with Git, GitHub, GitLab, and Bitbucket for source control operations."""

    def __init__(self):
        self._git_available = self._check_git()

    def _check_git(self) -> bool:
        try:
            result = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def _run_git(self, args: list, cwd: str = ".", timeout: int = 30) -> dict:
        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True, text=True, timeout=timeout, cwd=cwd or None,
            )
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        except subprocess.TimeoutExpired:
            return {"exit_code": -1, "stdout": "", "stderr": "Git command timed out"}
        except FileNotFoundError:
            return {"exit_code": -1, "stdout": "", "stderr": "Git not installed"}
        except Exception as e:
            return {"exit_code": -1, "stdout": "", "stderr": str(e)}

    # ── Git Operations ──

    def git_status(self, repo_path: str = ".") -> dict:
        r = self._run_git(["status", "--porcelain"], repo_path)
        changes = [line for line in r["stdout"].split("\n") if line.strip()]
        return {"status": "ok", "changes": changes, "clean": len(changes) == 0}

    def git_log(self, repo_path: str = ".", count: int = 20) -> dict:
        r = self._run_git(["log", "--oneline", f"-{count}"], repo_path)
        commits = [line for line in r["stdout"].split("\n") if line.strip()]
        return {"status": "ok", "commits": commits}

    def git_branch(self, repo_path: str = ".") -> dict:
        r = self._run_git(["branch", "-a"], repo_path)
        branches = [b.strip().replace("*", "").strip() for b in r["stdout"].split("\n") if b.strip()]
        return {"status": "ok", "branches": branches}

    def git_diff(self, repo_path: str = ".", staged: bool = False) -> dict:
        args = ["diff", "--staged"] if staged else ["diff"]
        r = self._run_git(args, repo_path)
        return {"status": "ok", "diff": r["stdout"][:10000]}

    def git_commit_analysis(self, repo_path: str = ".", commit_sha: str = "HEAD") -> dict:
        """Analyze a specific commit."""
        r = self._run_git(["show", "--stat", "--oneline", commit_sha], repo_path)
        return {"status": "ok", "commit": commit_sha, "details": r["stdout"][:5000]}

    def git_branch_health(self, repo_path: str = ".", branch: str = "") -> dict:
        """Check branch health: ahead/behind, conflicts, stale."""
        r = self._run_git(["status", "--porcelain", "-b"], repo_path)
        lines = r["stdout"].split("\n")
        branch_info = lines[0] if lines else ""

        ahead = 0
        behind = 0
        if "ahead" in branch_info:
            ahead_part = branch_info.split("ahead")[1].split("]")[0].strip()
            ahead = int(ahead_part) if ahead_part.isdigit() else 0
        if "behind" in branch_info:
            behind_part = branch_info.split("behind")[1].split("]")[0].strip()
            behind = int(behind_part) if behind_part.isdigit() else 0

        return {
            "status": "ok",
            "branch_info": branch_info,
            "ahead": ahead,
            "behind": behind,
            "healthy": ahead == 0 and behind == 0,
        }

    # ── GitHub API ──

    def _github_api(self, method: str, endpoint: str, data: dict = None) -> dict:
        import urllib.request
        url = f"https://api.github.com{endpoint}"
        headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "Jarvis-Ecosystem"}
        token = os.getenv("GITHUB_TOKEN", "")
        if token:
            headers["Authorization"] = f"token {token}"

        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return {"error": str(e)}

    def github_pr_review(self, repo: str, pr_number: int) -> dict:
        """Review a GitHub PR."""
        pr_data = self._github_api("GET", f"/repos/{repo}/pulls/{pr_number}")
        files = self._github_api("GET", f"/repos/{repo}/pulls/{pr_number}/files")
        reviews = self._github_api("GET", f"/repos/{repo}/pulls/{pr_number}/reviews")

        return {
            "status": "ok",
            "pr": {
                "number": pr_data.get("number"),
                "title": pr_data.get("title"),
                "state": pr_data.get("state"),
                "user": pr_data.get("user", {}).get("login"),
                "body": pr_data.get("body", "")[:2000],
                "additions": pr_data.get("additions"),
                "deletions": pr_data.get("deletions"),
                "changed_files": pr_data.get("changed_files"),
            },
            "files": [{"filename": f.get("filename"), "status": f.get("status"),
                        "additions": f.get("additions"), "deletions": f.get("deletions")}
                       for f in (files if isinstance(files, list) else [])],
            "reviews": [{"user": r.get("user", {}).get("login"), "state": r.get("state"),
                         "body": r.get("body", "")[:500]}
                        for r in (reviews if isinstance(reviews, list) else [])],
        }

    def github_commit_analysis(self, repo: str, sha: str) -> dict:
        """Analyze a GitHub commit."""
        commit = self._github_api("GET", f"/repos/{repo}/commits/{sha}")
        if "error" in commit:
            return commit
        return {
            "status": "ok",
            "sha": sha,
            "message": commit.get("commit", {}).get("message", ""),
            "author": commit.get("commit", {}).get("author", {}).get("name"),
            "date": commit.get("commit", {}).get("author", {}).get("date"),
            "stats": commit.get("stats", {}),
            "files": [{"filename": f.get("filename"), "status": f.get("status"),
                        "additions": f.get("additions"), "deletions": f.get("deletions")}
                       for f in commit.get("files", [])],
        }

    def github_release_summary(self, repo: str, limit: int = 5) -> dict:
        """Get release summaries."""
        releases = self._github_api("GET", f"/repos/{repo}/releases?per_page={limit}")
        if isinstance(releases, list):
            return {
                "status": "ok",
                "releases": [{
                    "tag": r.get("tag_name"),
                    "name": r.get("name"),
                    "body": r.get("body", "")[:1000],
                    "draft": r.get("draft"),
                    "prerelease": r.get("prerelease"),
                    "date": r.get("published_at"),
                } for r in releases],
            }
        return {"status": "error", "error": releases.get("error", "Unknown")}

    # ── GitLab API ──

    def _gitlab_api(self, endpoint: str, method: str = "GET", data: dict = None) -> dict:
        import urllib.request
        base_url = os.getenv("GITLAB_URL", "https://gitlab.com")
        url = f"{base_url}/api/v4{endpoint}"
        headers = {"Content-Type": "application/json"}
        token = os.getenv("GITLAB_TOKEN", "")
        if token:
            headers["PRIVATE-TOKEN"] = token

        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return {"error": str(e)}

    def gitlab_mr_review(self, project_id: int, mr_iid: int) -> dict:
        """Review a GitLab MR."""
        mr = self._gitlab_api(f"/projects/{project_id}/merge_requests/{mr_iid}")
        changes = self._gitlab_api(f"/projects/{project_id}/merge_requests/{mr_iid}/changes")

        return {
            "status": "ok",
            "mr": {
                "iid": mr.get("iid"),
                "title": mr.get("title"),
                "state": mr.get("state"),
                "author": mr.get("author", {}).get("username"),
                "description": mr.get("description", "")[:2000],
            },
            "changes": [{"old_path": c.get("old_path"), "new_path": c.get("new_path"),
                          "new_file": c.get("new_file"), "deleted_file": c.get("deleted_file")}
                         for c in changes.get("changes", [])],
        }

    # ── Bitbucket API ──

    def bitbucket_pr_review(self, workspace: str, repo_slug: str, pr_id: int) -> dict:
        """Review a Bitbucket PR."""
        import urllib.request
        url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}/pullrequests/{pr_id}"
        headers = {"Content-Type": "application/json"}
        token = os.getenv("BITBUCKET_TOKEN", "")
        if token:
            import base64
            credentials = base64.b64encode(token.encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                pr = json.loads(resp.read().decode())
                return {
                    "status": "ok",
                    "pr": {
                        "id": pr.get("id"),
                        "title": pr.get("title"),
                        "state": pr.get("state"),
                        "author": pr.get("author", {}).get("display_name"),
                        "description": pr.get("description", "")[:2000],
                    },
                }
        except Exception as e:
            return {"error": str(e)}


source_control = SourceControlIntegration()
