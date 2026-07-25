import re
from pathlib import Path
from typing import Optional

from ai.repo.languages import EXCLUDE_DIRS


KNOWLEDGE_PATTERNS = {
    "controllers": {
        "file_patterns": ["controller", "controllers", "handler", "handlers", "route", "routes"],
        "class_patterns": [r"(\w+)Controller", r"(\w+)Handler", r"(\w+)Resource"],
        "decorator_patterns": ["@app.route", "@router.get", "@router.post", "@router.put", "@router.delete",
                                "@Controller", "@RestController", "@RequestMapping"],
    },
    "services": {
        "file_patterns": ["service", "services"],
        "class_patterns": [r"(\w+)Service", r"(\w+)Manager", r"(\w+)Provider"],
        "decorator_patterns": ["@Service", "@Injectable"],
    },
    "models": {
        "file_patterns": ["model", "models", "entity", "entities", "schema", "schemas"],
        "class_patterns": [r"(\w+)Model", r"(\w+)Entity", r"(\w+)Schema", r"(\w+)Document"],
        "decorator_patterns": ["@Entity", "@Table", "@Model", "@Schema", "@Document"],
    },
    "repositories": {
        "file_patterns": ["repository", "repositories", "repo", "repos", "dao"],
        "class_patterns": [r"(\w+)Repository", r"(\w+)Repo", r"(\w+)DAO", r"(\w+)Gateway"],
        "decorator_patterns": ["@Repository"],
    },
    "routes": {
        "file_patterns": ["route", "routes", "router", "endpoints", "urls"],
        "content_patterns": [r"(?:app|router|Blueprint)\.(get|post|put|delete|patch|route)\s*\("],
    },
    "middleware": {
        "file_patterns": ["middleware", "middlewares", "interceptor", "interceptors", "filter", "filters"],
        "class_patterns": [r"(\w+)Middleware", r"(\w+)Interceptor", r"(\w+)Filter"],
        "decorator_patterns": ["@Middleware"],
    },
    "config": {
        "file_patterns": ["config", "configuration", "settings", "conf"],
        "file_exact": ["config.py", "settings.py", "config.json", "config.yaml", "config.yml",
                       "application.properties", "application.yml", ".env"],
    },
    "environment_files": {
        "file_exact": [".env", ".env.local", ".env.production", ".env.development", ".env.staging", ".env.example"],
    },
    "database_schema": {
        "file_patterns": ["migration", "migrations", "schema", "sql"],
        "file_extensions": [".sql"],
        "content_patterns": [r"CREATE\s+TABLE", r"ALTER\s+TABLE", r"CREATE\s+INDEX"],
    },
    "tests": {
        "file_patterns": ["test", "tests", "spec", "specs", "__tests__"],
        "file_prefixes": ["test_", "spec_"],
        "file_suffixes": ["_test", "_spec", ".test", ".spec"],
    },
    "ci_cd": {
        "file_exact": [".github/workflows", ".gitlab-ci.yml", "Jenkinsfile", ".circleci/config.yml",
                       "azure-pipelines.yml", "bitbucket-pipelines.yml"],
        "dir_patterns": [".github/workflows", ".gitlab-ci"],
    },
    "docker": {
        "file_exact": ["Dockerfile", "Dockerfile.dev", "Dockerfile.prod", "docker-compose.yml",
                       "docker-compose.yaml", "docker-compose.override.yml", ".dockerignore"],
    },
    "kubernetes": {
        "file_patterns": ["k8s", "kubernetes", "deploy", "deployment"],
        "file_extensions": [".yaml", ".yml"],
        "content_patterns": [r"apiVersion:\s*", r"kind:\s*(?:Pod|Deployment|Service|ConfigMap|Secret|Ingress)"],
    },
}


class RepositoryKnowledge:
    """Identifies architectural components: controllers, services, models,
    repositories, routes, middleware, config, env files, database schema,
    tests, CI/CD, Docker, Kubernetes."""

    def __init__(self, root: str = "."):
        self.root = Path(root).resolve()

    def identify(self) -> dict:
        result = {}

        for category, patterns in KNOWLEDGE_PATTERNS.items():
            items = self._identify_category(category, patterns)
            result[category] = items

        result["summary"] = {
            category: len(items) for category, items in result.items()
        }

        return result

    def _identify_category(self, category: str, patterns: dict) -> list:
        items = []
        seen = set()

        file_patterns = patterns.get("file_patterns", [])
        for fp in file_patterns:
            for filepath in self.root.rglob(f"*{fp}*"):
                if any(part in EXCLUDE_DIRS for part in filepath.parts):
                    continue
                key = str(filepath.relative_to(self.root))
                if key not in seen:
                    items.append({"file": key, "match": f"filename:{fp}"})
                    seen.add(key)

        file_exact = patterns.get("file_exact", [])
        for fe in file_exact:
            filepath = self.root / fe
            if filepath.exists():
                key = fe
                if key not in seen:
                    if filepath.is_dir():
                        count = sum(1 for _ in filepath.rglob("*") if _.is_file())
                        items.append({"dir": fe, "file_count": count, "match": "exact-dir"})
                    else:
                        items.append({"file": fe, "match": "exact-file"})
                    seen.add(key)

        file_prefixes = patterns.get("file_prefixes", [])
        for prefix in file_prefixes:
            for filepath in self.root.rglob(f"{prefix}*"):
                if any(part in EXCLUDE_DIRS for part in filepath.parts):
                    continue
                if filepath.is_file():
                    key = str(filepath.relative_to(self.root))
                    if key not in seen:
                        items.append({"file": key, "match": f"prefix:{prefix}"})
                        seen.add(key)

        file_suffixes = patterns.get("file_suffixes", [])
        for suffix in file_suffixes:
            for filepath in self.root.rglob(f"*{suffix}*"):
                if any(part in EXCLUDE_DIRS for part in filepath.parts):
                    continue
                if filepath.is_file():
                    key = str(filepath.relative_to(self.root))
                    if key not in seen:
                        items.append({"file": key, "match": f"suffix:{suffix}"})
                        seen.add(key)

        file_extensions = patterns.get("file_extensions", [])
        for ext in file_extensions:
            for filepath in self.root.rglob(f"*{ext}"):
                if any(part in EXCLUDE_DIRS for part in filepath.parts):
                    continue
                key = str(filepath.relative_to(self.root))
                if key not in seen:
                    items.append({"file": key, "match": f"extension:{ext}"})
                    seen.add(key)

        class_patterns = patterns.get("class_patterns", [])
        decorator_patterns = patterns.get("decorator_patterns", [])
        content_patterns = patterns.get("content_patterns", [])

        if class_patterns or decorator_patterns or content_patterns:
            for filepath in self._walk_source_files():
                if any(part in EXCLUDE_DIRS for part in filepath.parts):
                    continue
                key = str(filepath.relative_to(self.root))
                try:
                    content = filepath.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

                for cp in class_patterns:
                    for match in re.finditer(cp, content):
                        matched = match.group(0)
                        line = content[:match.start()].count("\n") + 1
                        entry_key = f"{key}:{line}"
                        if entry_key not in seen:
                            items.append({"file": key, "line": line, "match": matched, "type": "class_pattern"})
                            seen.add(entry_key)

                for dp in decorator_patterns:
                    if dp in content:
                        for match in re.finditer(re.escape(dp), content):
                            line = content[:match.start()].count("\n") + 1
                            entry_key = f"{key}:{line}"
                            if entry_key not in seen:
                                items.append({"file": key, "line": line, "match": dp, "type": "decorator"})
                                seen.add(entry_key)

                for ctp in content_patterns:
                    for match in re.finditer(ctp, content, re.IGNORECASE):
                        line = content[:match.start()].count("\n") + 1
                        entry_key = f"{key}:{line}"
                        if entry_key not in seen:
                            items.append({"file": key, "line": line, "match": match.group(0), "type": "content"})
                            seen.add(entry_key)

        dir_patterns = patterns.get("dir_patterns", [])
        for dp in dir_patterns:
            dirpath = self.root / dp
            if dirpath.is_dir():
                key = dp
                if key not in seen:
                    count = sum(1 for _ in dirpath.rglob("*") if _.is_file())
                    items.append({"dir": dp, "file_count": count, "match": "dir-pattern"})
                    seen.add(key)

        return items

    def _walk_source_files(self):
        source_extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cs", ".go", ".rs", ".php", ".sql", ".yaml", ".yml"}
        for filepath in self.root.rglob("*"):
            if not filepath.is_file():
                continue
            if filepath.suffix.lower() in source_extensions:
                yield filepath


repository_knowledge = RepositoryKnowledge()
