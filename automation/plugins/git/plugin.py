import subprocess
from typing import Any

from automation.engine.context import AutomationContext
from automation.engine.rollback import RollbackManager
from automation.plugins.base import AutomationPlugin, RiskLevel


class GitPlugin(AutomationPlugin):
    """Git version control automation plugin."""

    def __init__(self):
        super().__init__()
        self.name = "Git"
        self.description = "Git repository operations: status, commit, push, pull, branch, log, diff, merge, clone, stash"
        self.version = "1.0"
        self.author = "Jarvis"

    def initialize(self):
        self.register_action("git.status", self.status, RiskLevel.SAFE)
        self.register_action("git.log", self.log, RiskLevel.SAFE)
        self.register_action("git.diff", self.diff, RiskLevel.SAFE)
        self.register_action("git.branch", self.branch, RiskLevel.SAFE)
        self.register_action("git.add", self.add, RiskLevel.MEDIUM, requires_rollback=True)
        self.register_action("git.commit", self.commit, RiskLevel.MEDIUM, requires_rollback=True)
        self.register_action("git.push", self.push, RiskLevel.HIGH)
        self.register_action("git.pull", self.pull, RiskLevel.MEDIUM)
        self.register_action("git.clone", self.clone, RiskLevel.SAFE)
        self.register_action("git.stash", self.stash, RiskLevel.MEDIUM, requires_rollback=True)
        self.register_action("git.stash_pop", self.stash_pop, RiskLevel.MEDIUM)
        self.register_action("git.checkout", self.checkout, RiskLevel.MEDIUM, requires_rollback=True)
        self.register_action("git.merge", self.merge, RiskLevel.HIGH)
        self.register_action("git.create_branch", self.create_branch, RiskLevel.SAFE)
        self.register_action("git.fetch", self.fetch, RiskLevel.SAFE)
        self.register_action("git.remote", self.remote, RiskLevel.SAFE)
        self.register_action("git.init", self.init_repo, RiskLevel.SAFE)

        self.register_workflow({
            "id": "git_daily_workflow",
            "name": "Git Daily Workflow",
            "description": "Pull latest, check status, stage and commit changes",
            "version": "1.0",
            "variables": {"repo_path": ".", "commit_message": "Daily update"},
            "steps": [
                {"name": "pull", "type": "action", "action": "git.pull", "params": {"repo_path": "{{repo_path}}"}},
                {"name": "status", "type": "action", "action": "git.status", "params": {"repo_path": "{{repo_path}}"}},
                {"name": "add", "type": "action", "action": "git.add", "params": {"repo_path": "{{repo_path}}", "files": ["."]}},
                {"name": "commit", "type": "action", "action": "git.commit", "params": {"repo_path": "{{repo_path}}", "message": "{{commit_message}}"}},
            ],
        })

        self.register_workflow({
            "id": "git_feature_branch",
            "name": "Git Feature Branch",
            "description": "Create a new feature branch from current main",
            "version": "1.0",
            "variables": {"repo_path": ".", "branch_name": "feature/new"},
            "steps": [
                {"name": "fetch", "type": "action", "action": "git.fetch", "params": {"repo_path": "{{repo_path}}"}},
                {"name": "create_branch", "type": "action", "action": "git.create_branch", "params": {"repo_path": "{{repo_path}}", "branch": "{{branch_name}}"}},
                {"name": "checkout", "type": "action", "action": "git.checkout", "params": {"repo_path": "{{repo_path}}", "branch": "{{branch_name}}"}},
            ],
        })

    def _run_git(self, args: list[str], cwd: str = ".", timeout: int = 30) -> dict:
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

    def status(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        r = self._run_git(["status", "--porcelain"], params.get("repo_path", "."))
        changes = [line for line in r["stdout"].split("\n") if line.strip()]
        return {"status": "ok", "changes": changes, "clean": len(changes) == 0}

    def log(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        count = params.get("count", 20)
        r = self._run_git(["log", f"--oneline", f"-{count}"], params.get("repo_path", "."))
        commits = [line for line in r["stdout"].split("\n") if line.strip()]
        return {"status": "ok", "commits": commits}

    def diff(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        staged = params.get("staged", False)
        args = ["diff", "--staged"] if staged else ["diff"]
        r = self._run_git(args, params.get("repo_path", "."))
        return {"status": "ok", "diff": r["stdout"][:5000]}

    def branch(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        r = self._run_git(["branch", "-a"], params.get("repo_path", "."))
        branches = [b.strip().replace("*", "").strip() for b in r["stdout"].split("\n") if b.strip()]
        return {"status": "ok", "branches": branches}

    def add(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        repo = params.get("repo_path", ".")
        files = params.get("files", ["."])
        if isinstance(files, str):
            files = [files]
        r = self._run_git(["add"] + files, repo)
        rollback.register("git.add", lambda: self._run_git(["reset", "HEAD"] + files, repo), "Unstage files")
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"] or r["stderr"]}

    def commit(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        repo = params.get("repo_path", ".")
        message = params.get("message", "Automated commit by Jarvis")
        r = self._run_git(["commit", "-m", message], repo)
        if r["exit_code"] == 0:
            rollback.register("git.commit", lambda: self._run_git(["reset", "--soft", "HEAD~1"], repo), "Undo last commit")
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"] or r["stderr"]}

    def push(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        repo = params.get("repo_path", ".")
        remote = params.get("remote", "origin")
        branch = params.get("branch", "")
        args = ["push", remote]
        if branch:
            args.append(branch)
        r = self._run_git(args, repo, timeout=60)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"] or r["stderr"]}

    def pull(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        repo = params.get("repo_path", ".")
        remote = params.get("remote", "origin")
        branch = params.get("branch", "")
        args = ["pull", remote]
        if branch:
            args.append(branch)
        r = self._run_git(args, repo, timeout=60)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"] or r["stderr"]}

    def clone(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        url = params.get("url", "")
        dest = params.get("destination", "")
        args = ["clone", url]
        if dest:
            args.append(dest)
        r = self._run_git(args, timeout=120)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"] or r["stderr"]}

    def stash(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        repo = params.get("repo_path", ".")
        r = self._run_git(["stash"], repo)
        if r["exit_code"] == 0:
            rollback.register("git.stash", lambda: self._run_git(["stash", "pop"], repo), "Pop stash")
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"] or r["stderr"]}

    def stash_pop(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        r = self._run_git(["stash", "pop"], params.get("repo_path", "."))
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"] or r["stderr"]}

    def checkout(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        repo = params.get("repo_path", ".")
        branch = params.get("branch", "")
        r = self._run_git(["checkout", branch], repo)
        if r["exit_code"] == 0:
            rollback.register("git.checkout", lambda: self._run_git(["checkout", "-"], repo), "Checkout previous branch")
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"] or r["stderr"]}

    def merge(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        repo = params.get("repo_path", ".")
        branch = params.get("branch", "")
        r = self._run_git(["merge", branch], repo)
        if r["exit_code"] == 0:
            rollback.register("git.merge", lambda: self._run_git(["merge", "--abort"], repo), "Abort merge")
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"] or r["stderr"]}

    def create_branch(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        repo = params.get("repo_path", ".")
        branch = params.get("branch", "")
        r = self._run_git(["branch", branch], repo)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "branch": branch}

    def fetch(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        repo = params.get("repo_path", ".")
        remote = params.get("remote", "origin")
        r = self._run_git(["fetch", remote], repo, timeout=60)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"] or r["stderr"]}

    def remote(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        r = self._run_git(["remote", "-v"], params.get("repo_path", "."))
        remotes = [line for line in r["stdout"].split("\n") if line.strip()]
        return {"status": "ok", "remotes": remotes}

    def init_repo(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        repo = params.get("repo_path", ".")
        r = self._run_git(["init"], repo)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"] or r["stderr"]}
