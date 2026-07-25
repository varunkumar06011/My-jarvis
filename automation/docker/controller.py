import subprocess
from typing import Any

from automation.engine.context import AutomationContext
from automation.engine.rollback import RollbackManager


class DockerEngine:
    """Docker automation: containers, images, compose, volumes, networks."""

    def _run_docker(self, args: list[str], timeout: int = 30) -> dict:
        try:
            result = subprocess.run(
                ["docker"] + args,
                capture_output=True, text=True, timeout=timeout,
            )
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        except FileNotFoundError:
            return {"exit_code": -1, "stdout": "", "stderr": "Docker not installed"}
        except subprocess.TimeoutExpired:
            return {"exit_code": -1, "stdout": "", "stderr": "Timeout"}

    def ps(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        r = self._run_docker(["ps", "--format", "{{json .}}"])
        containers = [line for line in r["stdout"].split("\n") if line.strip()]
        return {"status": "ok", "containers": containers}

    def images(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        r = self._run_docker(["images", "--format", "{{json .}}"])
        images = [line for line in r["stdout"].split("\n") if line.strip()]
        return {"status": "ok", "images": images}

    def logs(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        container = params.get("container", "")
        lines = params.get("lines", 100)
        r = self._run_docker(["logs", "--tail", str(lines), container])
        return {"status": "ok", "container": container, "logs": r["stdout"][:5000]}

    def restart(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        container = params.get("container", "")
        r = self._run_docker(["restart", container])
        return {"status": "ok" if r["exit_code"] == 0 else "error", "container": container, "output": r["stdout"]}

    def stop(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        container = params.get("container", "")
        r = self._run_docker(["stop", container])
        rollback.register("docker.start", lambda: self._run_docker(["start", container]), f"Start {container}")
        return {"status": "ok" if r["exit_code"] == 0 else "error", "container": container}

    def start(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        container = params.get("container", "")
        r = self._run_docker(["start", container])
        return {"status": "ok" if r["exit_code"] == 0 else "error", "container": container}

    def compose_up(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        file = params.get("file", "docker-compose.yml")
        r = self._run_docker(["compose", "-f", file, "up", "-d"], timeout=120)
        rollback.register("docker.compose_down", lambda: self._run_docker(["compose", "-f", file, "down"]), f"Compose down {file}")
        return {"status": "ok" if r["exit_code"] == 0 else "error", "file": file}

    def compose_down(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        file = params.get("file", "docker-compose.yml")
        r = self._run_docker(["compose", "-f", file, "down"], timeout=60)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "file": file}

    def stats(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        r = self._run_docker(["stats", "--no-stream", "--format", "{{json .}}"])
        stats = [line for line in r["stdout"].split("\n") if line.strip()]
        return {"status": "ok", "stats": stats}

    def exec_cmd(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        container = params.get("container", "")
        cmd = params.get("command", "")
        r = self._run_docker(["exec", container, "sh", "-c", cmd])
        return {"status": "ok" if r["exit_code"] == 0 else "error", "stdout": r["stdout"][:5000], "stderr": r["stderr"][:2000]}

    def cleanup(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        r1 = self._run_docker(["container", "prune", "-f"])
        r2 = self._run_docker(["image", "prune", "-f"])
        return {"status": "ok", "containers_pruned": r1["stdout"], "images_pruned": r2["stdout"]}


docker_engine = DockerEngine()
