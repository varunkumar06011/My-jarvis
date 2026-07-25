import subprocess
import json
import os
from pathlib import Path
from typing import Optional

from core.event_bus import bus


class BuildSystemIntegration:
    """Integrates with Maven, Gradle, npm, pnpm, yarn, and pip build systems."""

    BUILD_SYSTEMS = {
        "maven": {"file": "pom.xml", "cmd": "mvn"},
        "gradle": {"file": "build.gradle", "cmd": "gradle"},
        "npm": {"file": "package.json", "cmd": "npm"},
        "pnpm": {"file": "pnpm-lock.yaml", "cmd": "pnpm"},
        "yarn": {"file": "yarn.lock", "cmd": "yarn"},
        "pip": {"file": "requirements.txt", "cmd": "pip"},
    }

    def __init__(self, root: str = "."):
        self.root = Path(root).resolve()

    def detect_build_systems(self) -> list:
        """Detect which build systems are present."""
        detected = []
        for name, info in self.BUILD_SYSTEMS.items():
            if (self.root / info["file"]).exists():
                detected.append(name)
        return detected

    def _run_command(self, cmd: list, cwd: str = ".", timeout: int = 120) -> dict:
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd or None,
            )
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        except subprocess.TimeoutExpired:
            return {"exit_code": -1, "stdout": "", "stderr": "Command timed out"}
        except FileNotFoundError:
            return {"exit_code": -1, "stdout": "", "stderr": f"{cmd[0]} not installed"}
        except Exception as e:
            return {"exit_code": -1, "stdout": "", "stderr": str(e)}

    # ── Maven ──

    def maven_build(self, cwd: str = ".", goals: str = "clean package") -> dict:
        r = self._run_command(["mvn"] + goals.split(), cwd=cwd, timeout=300)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"][-3000:] or r["stderr"][-3000:]}

    def maven_test(self, cwd: str = ".") -> dict:
        r = self._run_command(["mvn", "test"], cwd=cwd, timeout=300)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"][-3000:] or r["stderr"][-3000:]}

    def maven_dependencies(self, cwd: str = ".") -> dict:
        r = self._run_command(["mvn", "dependency:tree"], cwd=cwd, timeout=60)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "tree": r["stdout"][-5000:]}

    # ── Gradle ──

    def gradle_build(self, cwd: str = ".", tasks: str = "build") -> dict:
        r = self._run_command(["gradle"] + tasks.split(), cwd=cwd, timeout=300)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"][-3000:] or r["stderr"][-3000:]}

    def gradle_test(self, cwd: str = ".") -> dict:
        r = self._run_command(["gradle", "test"], cwd=cwd, timeout=300)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"][-3000:] or r["stderr"][-3000:]}

    def gradle_dependencies(self, cwd: str = ".") -> dict:
        r = self._run_command(["gradle", "dependencies"], cwd=cwd, timeout=60)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "tree": r["stdout"][-5000:]}

    # ── npm ──

    def npm_install(self, cwd: str = ".") -> dict:
        r = self._run_command(["npm", "install"], cwd=cwd, timeout=180)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"][-2000:] or r["stderr"][-2000:]}

    def npm_build(self, cwd: str = ".") -> dict:
        r = self._run_command(["npm", "run", "build"], cwd=cwd, timeout=180)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"][-2000:] or r["stderr"][-2000:]}

    def npm_test(self, cwd: str = ".") -> dict:
        r = self._run_command(["npm", "test"], cwd=cwd, timeout=180)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"][-2000:] or r["stderr"][-2000:]}

    def npm_audit(self, cwd: str = ".") -> dict:
        r = self._run_command(["npm", "audit", "--json"], cwd=cwd, timeout=60)
        try:
            audit = json.loads(r["stdout"])
            return {"status": "ok", "audit": audit}
        except Exception:
            return {"status": "ok", "output": r["stdout"][-2000:]}

    def npm_outdated(self, cwd: str = ".") -> dict:
        r = self._run_command(["npm", "outdated", "--json"], cwd=cwd, timeout=60)
        try:
            return {"status": "ok", "outdated": json.loads(r["stdout"] or "{}")}
        except Exception:
            return {"status": "ok", "output": r["stdout"][-2000:]}

    # ── pnpm ──

    def pnpm_install(self, cwd: str = ".") -> dict:
        r = self._run_command(["pnpm", "install"], cwd=cwd, timeout=180)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"][-2000:] or r["stderr"][-2000:]}

    def pnpm_build(self, cwd: str = ".") -> dict:
        r = self._run_command(["pnpm", "run", "build"], cwd=cwd, timeout=180)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"][-2000:] or r["stderr"][-2000:]}

    def pnpm_test(self, cwd: str = ".") -> dict:
        r = self._run_command(["pnpm", "test"], cwd=cwd, timeout=180)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"][-2000:] or r["stderr"][-2000:]}

    # ── yarn ──

    def yarn_install(self, cwd: str = ".") -> dict:
        r = self._run_command(["yarn", "install"], cwd=cwd, timeout=180)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"][-2000:] or r["stderr"][-2000:]}

    def yarn_build(self, cwd: str = ".") -> dict:
        r = self._run_command(["yarn", "build"], cwd=cwd, timeout=180)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"][-2000:] or r["stderr"][-2000:]}

    def yarn_test(self, cwd: str = ".") -> dict:
        r = self._run_command(["yarn", "test"], cwd=cwd, timeout=180)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"][-2000:] or r["stderr"][-2000:]}

    # ── pip ──

    def pip_install(self, cwd: str = ".", requirements: str = "requirements.txt") -> dict:
        r = self._run_command(["pip", "install", "-r", requirements], cwd=cwd, timeout=180)
        return {"status": "ok" if r["exit_code"] == 0 else "error", "output": r["stdout"][-2000:] or r["stderr"][-2000:]}

    def pip_list(self, cwd: str = ".") -> dict:
        r = self._run_command(["pip", "list", "--format", "json"], cwd=cwd, timeout=30)
        try:
            return {"status": "ok", "packages": json.loads(r["stdout"])}
        except Exception:
            return {"status": "ok", "output": r["stdout"][-2000:]}

    def pip_outdated(self, cwd: str = ".") -> dict:
        r = self._run_command(["pip", "list", "--outdated", "--format", "json"], cwd=cwd, timeout=60)
        try:
            return {"status": "ok", "outdated": json.loads(r["stdout"])}
        except Exception:
            return {"status": "ok", "output": r["stdout"][-2000:]}

    # ── Universal ──

    def build(self, system: str = None, cwd: str = ".") -> dict:
        """Run build using detected or specified build system."""
        if system is None:
            detected = self.detect_build_systems()
            if not detected:
                return {"error": "No build system detected"}
            system = detected[0]

        builders = {
            "maven": lambda: self.maven_build(cwd),
            "gradle": lambda: self.gradle_build(cwd),
            "npm": lambda: self.npm_build(cwd),
            "pnpm": lambda: self.pnpm_build(cwd),
            "yarn": lambda: self.yarn_build(cwd),
            "pip": lambda: {"status": "ok", "message": "pip doesn't have a build step — use install"},
        }

        builder = builders.get(system)
        if builder is None:
            return {"error": f"Unknown build system: {system}"}

        result = builder()
        bus.publish("BuildCompleted", {"system": system, "status": result.get("status")})
        return result

    def test(self, system: str = None, cwd: str = ".") -> dict:
        """Run tests using detected or specified build system."""
        if system is None:
            detected = self.detect_build_systems()
            if not detected:
                return {"error": "No build system detected"}
            system = detected[0]

        testers = {
            "maven": lambda: self.maven_test(cwd),
            "gradle": lambda: self.gradle_test(cwd),
            "npm": lambda: self.npm_test(cwd),
            "pnpm": lambda: self.pnpm_test(cwd),
            "yarn": lambda: self.yarn_test(cwd),
            "pip": lambda: {"status": "ok", "message": "Use pytest or unittest for Python tests"},
        }

        tester = testers.get(system)
        if tester is None:
            return {"error": f"Unknown build system: {system}"}

        result = tester()
        bus.publish("TestCompleted", {"system": system, "status": result.get("status")})
        return result


build_integration = BuildSystemIntegration()
