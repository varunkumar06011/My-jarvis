import ast
import re
from pathlib import Path
from typing import Optional
from collections import defaultdict

from core.event_bus import bus
from ai.repo.languages import EXCLUDE_DIRS


class BugDetector:
    """Detects dead code, circular dependencies, race conditions,
    memory leaks, null handling issues, resource leaks, and concurrency issues."""

    def __init__(self, root: str = "."):
        self.root = Path(root).resolve()

    def detect_all(self) -> dict:
        """Run all bug detection checks on the repository."""
        results = {
            "dead_code": self.detect_dead_code(),
            "circular_dependencies": self.detect_circular_dependencies(),
            "race_conditions": self.detect_race_conditions(),
            "memory_leaks": self.detect_memory_leaks(),
            "null_handling": self.detect_null_handling(),
            "resource_leaks": self.detect_resource_leaks(),
            "concurrency_issues": self.detect_concurrency_issues(),
        }

        total = sum(len(v) if isinstance(v, list) else len(v.get("issues", [])) for v in results.values())

        bus.publish("BugDetectionCompleted", {
            "root": str(self.root),
            "total_issues": total,
        })

        results["summary"] = {
            "total_issues": total,
            "by_type": {k: len(v) if isinstance(v, list) else len(v.get("issues", [])) for k, v in results.items() if k != "summary"},
        }

        return results

    def detect_dead_code(self) -> list:
        """Find unused functions, classes, and imports."""
        issues = []

        defined_symbols = {}
        used_symbols = set()

        for filepath in self._walk_python_files():
            rel = str(filepath.relative_to(self.root)).replace("\\", "/")
            try:
                source = filepath.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not node.name.startswith("_"):
                        defined_symbols[f"{rel}:{node.name}"] = {"file": rel, "line": node.lineno, "name": node.name}
                elif isinstance(node, ast.ClassDef):
                    defined_symbols[f"{rel}:{node.name}"] = {"file": rel, "line": node.lineno, "name": node.name, "type": "class"}
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        used_symbols.add(node.func.id)
                    elif isinstance(node.func, ast.Attribute):
                        used_symbols.add(node.func.attr)

        for key, info in defined_symbols.items():
            if info["name"] not in used_symbols:
                issues.append({
                    "type": "dead_code",
                    "severity": "low",
                    "file": info["file"],
                    "line": info["line"],
                    "message": f"{'Class' if info.get('type') == 'class' else 'Function'} '{info['name']}' is never called",
                })

        return issues

    def detect_circular_dependencies(self) -> list:
        """Detect circular import dependencies."""
        issues = []
        import_graph = defaultdict(list)

        for filepath in self._walk_python_files():
            rel = str(filepath.relative_to(self.root)).replace("\\", "/")
            module = rel.replace("/", ".").replace(".py", "")

            try:
                source = filepath.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module:
                        import_graph[module].append(node.module)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        import_graph[module].append(alias.name)

        visited = set()
        rec_stack = set()

        def has_cycle(node, path):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in import_graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, path + [neighbor]):
                        return True
                elif neighbor in rec_stack:
                    issues.append({
                        "type": "circular_dependency",
                        "severity": "high",
                        "modules": path + [neighbor],
                        "message": f"Circular dependency: {' → '.join(path + [neighbor])}",
                    })
                    return True

            rec_stack.discard(node)
            return False

        for module in import_graph:
            if module not in visited:
                has_cycle(module, [module])

        return issues

    def detect_race_conditions(self) -> list:
        """Detect potential race conditions."""
        issues = []

        for filepath in self._walk_python_files():
            rel = str(filepath.relative_to(self.root)).replace("\\", "/")
            try:
                source = filepath.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)
            except Exception:
                continue

            shared_vars = set()
            thread_creation = False
            lock_usage = False

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = self._get_name(node.func)
                    if func_name in ("Thread", "Lock", "RLock", "Semaphore"):
                        if func_name == "Thread":
                            thread_creation = True
                        elif func_name in ("Lock", "RLock", "Semaphore"):
                            lock_usage = True

                if isinstance(node, ast.Global):
                    for name in node.names:
                        shared_vars.add(name)

            if thread_creation and shared_vars and not lock_usage:
                issues.append({
                    "type": "race_condition",
                    "severity": "high",
                    "file": rel,
                    "message": f"Thread creation with shared global variables ({', '.join(shared_vars)}) but no lock usage",
                })

            if thread_creation:
                for node in ast.walk(tree):
                    if isinstance(node, ast.AugAssign):
                        if isinstance(node.target, ast.Name) and node.target.id in shared_vars:
                            issues.append({
                                "type": "race_condition",
                                "severity": "high",
                                "file": rel,
                                "line": node.lineno,
                                "message": f"Non-atomic operation on shared variable '{node.target.id}' in threaded context",
                            })

        return issues

    def detect_memory_leaks(self) -> list:
        """Detect potential memory leaks."""
        issues = []

        for filepath in self._walk_python_files():
            rel = str(filepath.relative_to(self.root)).replace("\\", "/")
            try:
                source = filepath.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    has_init = False
                    has_del = False
                    has_close = False

                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if item.name == "__init__":
                                has_init = True
                            elif item.name == "__del__":
                                has_del = True
                            elif item.name == "close":
                                has_close = True

                    init_assigns = []
                    if has_init:
                        for item in node.body:
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__":
                                for assign in ast.walk(item):
                                    if isinstance(assign, ast.Assign):
                                        for target in assign.targets:
                                            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                                                if target.value.id == "self":
                                                    init_assigns.append(target.attr)

                    resource_patterns = ["conn", "connection", "cursor", "file", "socket", "client", "session", "pool"]
                    has_resource = any(any(rp in attr.lower() for rp in resource_patterns) for attr in init_assigns)

                    if has_resource and not has_del and not has_close:
                        issues.append({
                            "type": "memory_leak",
                            "severity": "medium",
                            "file": rel,
                            "line": node.lineno,
                            "message": f"Class '{node.name}' allocates resources in __init__ but has no __del__ or close() method",
                        })

            if re.search(r'open\s*\([^)]+\)(?!\s*as\s)', source):
                for match in re.finditer(r'(\w+)\s*=\s*open\s*\(', source):
                    line = source[:match.start()].count("\n") + 1
                    issues.append({
                        "type": "resource_leak",
                        "severity": "medium",
                        "file": rel,
                        "line": line,
                        "message": "File opened without 'with' statement — may not be properly closed",
                    })

        return issues

    def detect_null_handling(self) -> list:
        """Detect potential null/None handling issues."""
        issues = []

        for filepath in self._walk_python_files():
            rel = str(filepath.relative_to(self.root)).replace("\\", "/")
            try:
                source = filepath.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Call):
                        inner_func = node.func.value
                        if isinstance(inner_func.func, ast.Name):
                            func_name = inner_func.func.id
                            if func_name in ("get", "getattr", "dict", "json.loads", "requests.get", "requests.post"):
                                attr_name = node.func.attr
                                issues.append({
                                    "type": "null_handling",
                                    "severity": "medium",
                                    "file": rel,
                                    "line": node.lineno,
                                    "message": f"Chained call .{attr_name}() on result of {func_name}() — may return None",
                                })

                if isinstance(node, ast.Subscript):
                    if isinstance(node.value, ast.Call):
                        func_name = self._get_name(node.value.func)
                        if func_name in ("get", "json.loads", "eval"):
                            issues.append({
                                "type": "null_handling",
                                "severity": "medium",
                                "file": rel,
                                "line": node.lineno,
                                "message": f"Subscript access on result of {func_name}() — may return None or empty",
                            })

        return issues

    def detect_resource_leaks(self) -> list:
        """Detect file/socket/database resource leaks."""
        issues = []

        for filepath in self._walk_python_files():
            rel = str(filepath.relative_to(self.root)).replace("\\", "/")
            try:
                source = filepath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            resource_patterns = [
                (r'(\w+)\s*=\s*open\s*\(', "file"),
                (r'(\w+)\s*=\s*socket\.', "socket"),
                (r'(\w+)\s*=\s*\w+\.connect\(', "database"),
                (r'(\w+)\s*=\s*\w+\.cursor\(', "cursor"),
            ]

            for pattern, resource_type in resource_patterns:
                for match in re.finditer(pattern, source):
                    var_name = match.group(1)
                    line = source[:match.start()].count("\n") + 1

                    if not re.search(rf'{var_name}\.close\s*\(\s*\)', source):
                        if not re.search(rf'with\s+.*{var_name}', source):
                            issues.append({
                                "type": "resource_leak",
                                "severity": "medium",
                                "file": rel,
                                "line": line,
                                "message": f"{resource_type} resource '{var_name}' opened but never closed",
                            })

        return issues

    def detect_concurrency_issues(self) -> list:
        """Detect concurrency issues beyond race conditions."""
        issues = []

        for filepath in self._walk_python_files():
            rel = str(filepath.relative_to(self.root)).replace("\\", "/")
            try:
                source = filepath.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.With):
                    for item in node.items:
                        if isinstance(item.context_expr, ast.Call):
                            func_name = self._get_name(item.context_expr.func)
                            if func_name and "lock" in func_name.lower():
                                break
                    else:
                        for item in node.items:
                            if isinstance(item.context_expr, ast.Call):
                                func_name = self._get_name(item.context_expr.func)
                                if func_name in ("Thread", "Process"):
                                    issues.append({
                                        "type": "concurrency",
                                        "severity": "low",
                                        "file": rel,
                                        "line": node.lineno,
                                        "message": "Thread/Process created without synchronization context",
                                    })

                if isinstance(node, ast.AsyncFunctionDef):
                    has_await = False
                    for child in ast.walk(node):
                        if isinstance(child, ast.Await):
                            has_await = True
                            break

                    if not has_await and node.name.startswith("async_"):
                        issues.append({
                            "type": "concurrency",
                            "severity": "low",
                            "file": rel,
                            "line": node.lineno,
                            "message": f"Async function '{node.name}' has no await — may not be truly async",
                        })

        return issues

    def _walk_python_files(self):
        for filepath in self.root.rglob("*.py"):
            if any(part in EXCLUDE_DIRS for part in filepath.parts):
                continue
            yield filepath

    def _get_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            parts = []
            while isinstance(node, ast.Attribute):
                parts.append(node.attr)
                node = node.value
            if isinstance(node, ast.Name):
                parts.append(node.id)
            return ".".join(reversed(parts))
        return ""


bug_detector = BugDetector()
