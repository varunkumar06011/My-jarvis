import subprocess
import json
import os
from pathlib import Path
from typing import Optional

from core.event_bus import bus


class ContainerIntegration:
    """Integrates with Docker and Docker Compose for containerization operations."""

    def __init__(self):
        self._docker_available = self._check_docker()

    def _check_docker(self) -> bool:
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def _run_docker(self, args: list, timeout: int = 60) -> dict:
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
        except subprocess.TimeoutExpired:
            return {"exit_code": -1, "stdout": "", "stderr": "Docker command timed out"}
        except FileNotFoundError:
            return {"exit_code": -1, "stdout": "", "stderr": "Docker not installed"}
        except Exception as e:
            return {"exit_code": -1, "stdout": "", "stderr": str(e)}

    def _run_compose(self, args: list, cwd: str = ".", timeout: int = 120) -> dict:
        try:
            result = subprocess.run(
                ["docker-compose"] + args,
                capture_output=True, text=True, timeout=timeout, cwd=cwd or None,
            )
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        except subprocess.TimeoutExpired:
            return {"exit_code": -1, "stdout": "", "stderr": "Docker compose command timed out"}
        except FileNotFoundError:
            return {"exit_code": -1, "stdout": "", "stderr": "Docker compose not installed"}
        except Exception as e:
            return {"exit_code": -1, "stdout": "", "stderr": str(e)}

    # ── Docker Operations ──

    def docker_status(self) -> dict:
        """Check Docker daemon status."""
        if not self._docker_available:
            return {"status": "error", "error": "Docker not installed"}
        r = self._run_docker(["info", "--format", "{{json .}}"], timeout=10)
        if r["exit_code"] == 0:
            try:
                info = json.loads(r["stdout"])
                return {
                    "status": "ok",
                    "running": True,
                    "containers": info.get("Containers", 0),
                    "images": info.get("Images", 0),
                    "version": info.get("ServerVersion", "unknown"),
                }
            except Exception:
                return {"status": "ok", "running": True, "raw": r["stdout"][:500]}
        return {"status": "error", "running": False, "error": r["stderr"]}

    def docker_build(self, dockerfile: str = "Dockerfile", tag: str = "", context: str = ".") -> dict:
        """Build a Docker image."""
        args = ["build", "-f", dockerfile]
        if tag:
            args.extend(["-t", tag])
        args.append(context)
        r = self._run_docker(args, timeout=300)
        return {
            "status": "ok" if r["exit_code"] == 0 else "error",
            "tag": tag,
            "output": r["stdout"][-2000:] or r["stderr"][-2000:],
        }

    def docker_run(self, image: str, ports: dict = None, env: dict = None,
                   volumes: dict = None, detached: bool = True, name: str = "") -> dict:
        """Run a Docker container."""
        args = ["run"]
        if detached:
            args.append("-d")
        if name:
            args.extend(["--name", name])
        if ports:
            for host_port, container_port in ports.items():
                args.extend(["-p", f"{host_port}:{container_port}"])
        if env:
            for key, value in env.items():
                args.extend(["-e", f"{key}={value}"])
        if volumes:
            for host_path, container_path in volumes.items():
                args.extend(["-v", f"{host_path}:{container_path}"])
        args.append(image)

        r = self._run_docker(args, timeout=60)
        return {
            "status": "ok" if r["exit_code"] == 0 else "error",
            "container_id": r["stdout"][:12] if r["exit_code"] == 0 else None,
            "output": r["stderr"][-1000:],
        }

    def docker_ps(self, all_containers: bool = False) -> dict:
        """List Docker containers."""
        args = ["ps", "--format", "{{json .}}"]
        if all_containers:
            args.append("-a")
        r = self._run_docker(args, timeout=10)
        if r["exit_code"] == 0:
            containers = []
            for line in r["stdout"].split("\n"):
                if line.strip():
                    try:
                        containers.append(json.loads(line))
                    except Exception:
                        pass
            return {"status": "ok", "containers": containers}
        return {"status": "error", "error": r["stderr"]}

    def docker_stop(self, container_id: str) -> dict:
        """Stop a Docker container."""
        r = self._run_docker(["stop", container_id], timeout=30)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"] or r["stderr"]}

    def docker_remove(self, container_id: str) -> dict:
        """Remove a Docker container."""
        r = self._run_docker(["rm", "-f", container_id], timeout=30)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"] or r["stderr"]}

    def docker_images(self) -> dict:
        """List Docker images."""
        r = self._run_docker(["images", "--format", "{{json .}}"], timeout=10)
        if r["exit_code"] == 0:
            images = []
            for line in r["stdout"].split("\n"):
                if line.strip():
                    try:
                        images.append(json.loads(line))
                    except Exception:
                        pass
            return {"status": "ok", "images": images}
        return {"status": "error", "error": r["stderr"]}

    def docker_logs(self, container_id: str, tail: int = 100) -> dict:
        """Get Docker container logs."""
        r = self._run_docker(["logs", "--tail", str(tail), container_id], timeout=30)
        return {"status": "ok", "logs": r["stdout"][-3000:] if r["stdout"] else r["stderr"][-3000:]}

    # ── Docker Compose Operations ──

    def compose_up(self, cwd: str = ".", detached: bool = True, service: str = "") -> dict:
        """Start Docker Compose services."""
        args = ["up"]
        if detached:
            args.append("-d")
        if service:
            args.append(service)
        r = self._run_compose(args, cwd=cwd, timeout=180)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"][-2000:] or r["stderr"][-2000:]}

    def compose_down(self, cwd: str = ".", volumes: bool = False) -> dict:
        """Stop Docker Compose services."""
        args = ["down"]
        if volumes:
            args.append("-v")
        r = self._run_compose(args, cwd=cwd, timeout=60)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"][-1000:] or r["stderr"][-1000:]}

    def compose_ps(self, cwd: str = ".") -> dict:
        """List Docker Compose services."""
        r = self._run_compose(["ps"], cwd=cwd, timeout=10)
        return {"status": "ok", "output": r["stdout"]}

    def compose_logs(self, cwd: str = ".", service: str = "", tail: int = 100) -> dict:
        """Get Docker Compose logs."""
        args = ["logs", "--tail", str(tail)]
        if service:
            args.append(service)
        r = self._run_compose(args, cwd=cwd, timeout=30)
        return {"status": "ok", "logs": r["stdout"][-3000:]}

    def compose_config(self, cwd: str = ".") -> dict:
        """Validate and view Docker Compose configuration."""
        r = self._run_compose(["config"], cwd=cwd, timeout=10)
        if r["exit_code"] == 0:
            return {"status": "ok", "config": r["stdout"][:5000]}
        return {"status": "error", "error": r["stderr"]}

    def analyze_dockerfile(self, dockerfile_path: str = "Dockerfile") -> dict:
        """Analyze a Dockerfile for best practices."""
        filepath = Path(dockerfile_path)
        if not filepath.is_absolute():
            filepath = Path.cwd() / dockerfile_path

        if not filepath.exists():
            return {"error": f"Dockerfile not found: {dockerfile_path}"}

        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {"error": str(e)}

        issues = []
        lines = content.split("\n")

        has_multistage = False
        has_healthcheck = False
        has_nonroot_user = False
        base_image = ""

        for line in lines:
            stripped = line.strip().upper()
            if stripped.startswith("FROM"):
                if " AS " in stripped or " as " in line:
                    has_multistage = True
                parts = line.split()
                if len(parts) >= 2:
                    base_image = parts[1]
                if ":latest" in stripped:
                    issues.append({"severity": "medium", "message": "Using :latest tag — pin specific version"})
            elif stripped.startswith("HEALTHCHECK"):
                has_healthcheck = True
            elif stripped.startswith("USER"):
                has_nonroot_user = True
            elif stripped.startswith("ADD"):
                issues.append({"severity": "low", "message": "Using ADD instead of COPY — use COPY for files"})

        if not has_multistage:
            issues.append({"severity": "low", "message": "No multi-stage build — consider for smaller images"})
        if not has_healthcheck:
            issues.append({"severity": "medium", "message": "No HEALTHCHECK instruction — add for production"})
        if not has_nonroot_user:
            issues.append({"severity": "high", "message": "No USER instruction — running as root is insecure"})

        return {
            "status": "ok",
            "base_image": base_image,
            "has_multistage": has_multistage,
            "has_healthcheck": has_healthcheck,
            "has_nonroot_user": has_nonroot_user,
            "issues": issues,
            "line_count": len(lines),
        }


container_integration = ContainerIntegration()
