import json
import re
from pathlib import Path
from typing import Optional


FRAMEWORK_SIGNATURES = {
    "React": {
        "files": ["package.json"],
        "deps": ["react", "react-dom"],
        "extensions": [".jsx", ".tsx"],
        "dirs": ["src/components", "src/pages"],
    },
    "Angular": {
        "files": ["angular.json"],
        "deps": ["@angular/core"],
        "extensions": [".ts"],
        "dirs": ["src/app"],
    },
    "Vue": {
        "files": ["vue.config.js"],
        "deps": ["vue"],
        "extensions": [".vue"],
        "dirs": ["src/components"],
    },
    "Node": {
        "files": ["package.json"],
        "deps": ["express", "fastify", "koa"],
        "extensions": [".js"],
        "dirs": [],
    },
    "Express": {
        "files": ["package.json"],
        "deps": ["express"],
        "extensions": [".js"],
        "dirs": [],
    },
    "FastAPI": {
        "files": ["requirements.txt", "pyproject.toml"],
        "deps": ["fastapi"],
        "extensions": [".py"],
        "dirs": [],
    },
    "Django": {
        "files": ["requirements.txt", "manage.py"],
        "deps": ["django"],
        "extensions": [".py"],
        "dirs": [],
    },
    "Spring Boot": {
        "files": ["pom.xml", "build.gradle"],
        "deps": ["spring-boot"],
        "extensions": [".java"],
        "dirs": ["src/main/java"],
    },
    ".NET": {
        "files": ["*.csproj"],
        "deps": [],
        "extensions": [".cs"],
        "dirs": [],
    },
    "Laravel": {
        "files": ["composer.json"],
        "deps": ["laravel/framework"],
        "extensions": [".php"],
        "dirs": ["app/Http"],
    },
    "Next.js": {
        "files": ["package.json", "next.config.js"],
        "deps": ["next"],
        "extensions": [".js", ".jsx", ".ts", ".tsx"],
        "dirs": ["pages", "app", "src/pages", "src/app"],
    },
    "NestJS": {
        "files": ["package.json", "nest-cli.json"],
        "deps": ["@nestjs/core"],
        "extensions": [".ts"],
        "dirs": ["src/modules"],
    },
}


class FrameworkDetector:
    """Automatically recognizes web frameworks used in a repository."""

    def __init__(self, root: str = "."):
        self.root = Path(root).resolve()

    def detect(self) -> dict:
        detected = []

        for framework, sig in FRAMEWORK_SIGNATURES.items():
            score = 0
            evidence = []

            for filename in sig["files"]:
                if "*" in filename:
                    if list(self.root.glob(filename)):
                        score += 2
                        evidence.append(f"file: {filename}")
                elif (self.root / filename).exists():
                    score += 2
                    evidence.append(f"file: {filename}")

                    if filename == "package.json":
                        deps = self._read_package_json_deps()
                        for dep in sig["deps"]:
                            if dep in deps:
                                score += 3
                                evidence.append(f"dep: {dep}")

                    elif filename in ("requirements.txt", "pyproject.toml"):
                        content = self._read_file(filename)
                        if content:
                            for dep in sig["deps"]:
                                if dep.lower() in content.lower():
                                    score += 3
                                    evidence.append(f"dep: {dep}")

                    elif filename in ("pom.xml", "build.gradle"):
                        content = self._read_file(filename)
                        if content:
                            for dep in sig["deps"]:
                                if dep.lower() in content.lower():
                                    score += 3
                                    evidence.append(f"dep: {dep}")

                    elif filename == "composer.json":
                        deps = self._read_composer_deps()
                        for dep in sig["deps"]:
                            if dep in deps:
                                score += 3
                                evidence.append(f"dep: {dep}")

            for ext in sig["extensions"]:
                files = list(self.root.rglob(f"*{ext}"))
                files = [f for f in files if not any(p in {"node_modules", "venv", ".git", "__pycache__", "dist", "build"} for p in f.parts)]
                if files:
                    score += min(len(files), 5)
                    evidence.append(f"{len(files)} {ext} files")

            for directory in sig["dirs"]:
                if (self.root / directory).is_dir():
                    score += 2
                    evidence.append(f"dir: {directory}")

            if score >= 3:
                detected.append({
                    "framework": framework,
                    "confidence": "high" if score >= 8 else "medium" if score >= 5 else "low",
                    "score": score,
                    "evidence": evidence,
                })

        detected.sort(key=lambda x: x["score"], reverse=True)

        return {
            "frameworks": detected,
            "primary_framework": detected[0]["framework"] if detected else None,
        }

    def _read_file(self, filename: str) -> Optional[str]:
        filepath = self.root / filename
        if filepath.exists():
            try:
                return filepath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass
        return None

    def _read_package_json_deps(self) -> dict:
        filepath = self.root / "package.json"
        if not filepath.exists():
            return {}
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            deps = {}
            deps.update(data.get("dependencies", {}))
            deps.update(data.get("devDependencies", {}))
            return deps
        except Exception:
            return {}

    def _read_composer_deps(self) -> dict:
        filepath = self.root / "composer.json"
        if not filepath.exists():
            return {}
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            deps = {}
            deps.update(data.get("require", {}))
            deps.update(data.get("require-dev", {}))
            return deps
        except Exception:
            return {}


framework_detector = FrameworkDetector()
