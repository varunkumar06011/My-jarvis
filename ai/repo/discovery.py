import os
import json
import subprocess
from pathlib import Path
from typing import Optional

from core.event_bus import bus


class RepositoryDiscovery:
    """Detects repository structure: root, monorepos, submodules, workspaces,
    package managers, and build systems."""

    MARKERS = {
        ".git": "git",
        ".hg": "mercurial",
        ".svn": "subversion",
    }

    MONOREPO_MARKERS = {
        "pnpm-workspace.yaml": "pnpm",
        "lerna.json": "lerna",
        "nx.json": "nx",
        "turbo.json": "turbo",
        "rush.json": "rush",
    }

    PACKAGE_MANAGERS = {
        "package.json": "npm",
        "yarn.lock": "yarn",
        "pnpm-lock.yaml": "pnpm",
        "package-lock.json": "npm",
        "requirements.txt": "pip",
        "Pipfile": "pipenv",
        "poetry.lock": "poetry",
        "pyproject.toml": "poetry",
        "go.mod": "go",
        "Cargo.toml": "cargo",
        "pom.xml": "maven",
        "build.gradle": "gradle",
        "build.gradle.kts": "gradle",
        "Gemfile": "bundler",
        "composer.json": "composer",
        "packages.config": "nuget",
        "*.csproj": "dotnet",
    }

    BUILD_SYSTEMS = {
        "Makefile": "make",
        "CMakeLists.txt": "cmake",
        "build.gradle": "gradle",
        "build.gradle.kts": "gradle",
        "pom.xml": "maven",
        "package.json": "npm",
        "webpack.config.js": "webpack",
        "vite.config.js": "vite",
        "vite.config.ts": "vite",
        "rollup.config.js": "rollup",
        "tsconfig.json": "tsc",
        "Cargo.toml": "cargo",
        "setup.py": "setuptools",
        "setup.cfg": "setuptools",
        "pyproject.toml": "build",
        "Dockerfile": "docker",
        "docker-compose.yml": "docker-compose",
        "docker-compose.yaml": "docker-compose",
        "Bazel": "bazel",
        "WORKSPACE": "bazel",
        "BUILD": "bazel",
        "build.sbt": "sbt",
        "project.clj": "leiningen",
    }

    def __init__(self, root: str = "."):
        self.root = Path(root).resolve()

    def discover(self) -> dict:
        result = {
            "root": str(self.root),
            "vcs": self._detect_vcs(),
            "is_monorepo": self._detect_monorepo(),
            "submodules": self._detect_submodules(),
            "workspaces": self._detect_workspaces(),
            "package_managers": self._detect_package_managers(),
            "build_systems": self._detect_build_systems(),
            "top_level_dirs": self._top_level_dirs(),
            "top_level_files": self._top_level_files(),
        }

        bus.publish("RepositoryDiscovered", {"root": str(self.root), "vcs": result["vcs"]})
        return result

    def _detect_vcs(self) -> Optional[str]:
        for marker, vcs in self.MARKERS.items():
            if (self.root / marker).is_dir():
                return vcs
        return None

    def _detect_monorepo(self) -> Optional[dict]:
        for marker, tool in self.MONOREPO_MARKERS.items():
            filepath = self.root / marker
            if filepath.exists():
                packages = []
                try:
                    if marker == "pnpm-workspace.yaml":
                        content = filepath.read_text(encoding="utf-8", errors="replace")
                        for line in content.splitlines():
                            line = line.strip()
                            if line.startswith("- "):
                                packages.append(line[2:].strip().strip('"'))
                    elif marker == "lerna.json":
                        data = json.loads(filepath.read_text(encoding="utf-8"))
                        packages = data.get("packages", ["packages/*"])
                    elif marker == "nx.json":
                        packages = self._nx_projects()
                    elif marker == "turbo.json":
                        packages = self._turbo_packages()
                    elif marker == "rush.json":
                        data = json.loads(filepath.read_text(encoding="utf-8"))
                        packages = [p.get("projectFolder", "") for p in data.get("projects", [])]
                except Exception:
                    pass
                return {"tool": tool, "packages": packages}

        if (self.root / "packages").is_dir():
            packages = [d.name for d in (self.root / "packages").iterdir() if d.is_dir() and not d.name.startswith(".")]
            if packages:
                return {"tool": "directory-based", "packages": packages}

        return None

    def _nx_projects(self) -> list:
        projects = []
        project_config = self.root / "workspace.json"
        if project_config.exists():
            try:
                data = json.loads(project_config.read_text(encoding="utf-8"))
                projects = list(data.get("projects", {}).keys())
            except Exception:
                pass
        return projects

    def _turbo_packages(self) -> list]:
        packages = []
        pkg = self.root / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8"))
                packages = data.get("workspaces", [])
            except Exception:
                pass
        return packages

    def _detect_submodules(self) -> list:
        gitmodules = self.root / ".gitmodules"
        if not gitmodules.exists():
            return []

        submodules = []
        try:
            content = gitmodules.read_text(encoding="utf-8", errors="replace")
            current = {}
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("[submodule"):
                    if current:
                        submodules.append(current)
                    current = {}
                elif "=" in line:
                    key, val = line.split("=", 1)
                    current[key.strip()] = val.strip()
            if current:
                submodules.append(current)
        except Exception:
            pass

        return submodules

    def _detect_workspaces(self) -> list:
        workspaces = []
        pkg = self.root / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8"))
                ws = data.get("workspaces", [])
                if isinstance(ws, list):
                    workspaces = ws
                elif isinstance(ws, dict):
                    workspaces = ws.get("packages", [])
            except Exception:
                pass

        cargo = self.root / "Cargo.toml"
        if cargo.exists():
            try:
                content = cargo.read_text(encoding="utf-8", errors="replace")
                if "[workspace]" in content:
                    workspaces.append("cargo-workspace")
            except Exception:
                pass

        return workspaces

    def _detect_package_managers(self) -> list:
        found = []
        for marker, pm in self.PACKAGE_MANAGERS.items():
            if "*" in marker:
                pattern = marker
                if list(self.root.glob(pattern)):
                    found.append(pm)
            elif (self.root / marker).exists():
                found.append(pm)
        return sorted(set(found))

    def _detect_build_systems(self) -> list:
        found = []
        for marker, bs in self.BUILD_SYSTEMS.items():
            if (self.root / marker).exists():
                found.append(bs)
        return sorted(set(found))

    def _top_level_dirs(self) -> list:
        exclude = {".git", ".hg", ".svn", "node_modules", "venv", "__pycache__", ".idea", ".vscode"}
        return [d.name for d in self.root.iterdir() if d.is_dir() and d.name not in exclude and not d.name.startswith(".")]

    def _top_level_files(self) -> list:
        return [f.name for f in self.root.iterdir() if f.is_file() and not f.name.startswith(".")]


repo_discovery = RepositoryDiscovery()
