import ast
import json
import re
import os
from collections import defaultdict
from pathlib import Path
from typing import Optional

from core.event_bus import bus
from ai.repo.languages import LANGUAGE_MAP, EXCLUDE_DIRS


class StaticAnalyzer:
    """Builds AST, symbol index, type index, import graph, dependency graph,
    module graph, call graph, class hierarchy, API graph, database graph,
    and configuration graph for a repository."""

    def __init__(self, root: str = "."):
        self.root = Path(root).resolve()
        self._ast_cache: dict[str, ast.AST] = {}
        self._symbols: dict[str, dict] = {}
        self._types: dict[str, dict] = {}
        self._imports: dict[str, list[str]] = {}
        self._dependencies: dict[str, list[str]] = {}
        self._modules: dict[str, dict] = {}
        self._calls: dict[str, list[str]] = {}
        self._class_hierarchy: dict[str, list[str]] = {}
        self._api_endpoints: list[dict] = []
        self._db_entities: list[dict] = []
        self._config_entries: list[dict] = {}

    def analyze(self) -> dict:
        self._reset()

        py_files = self._collect_python_files()
        js_files = self._collect_js_files()

        for filepath in py_files:
            self._analyze_python(filepath)

        for filepath in js_files:
            self._analyze_javascript(filepath)

        self._build_class_hierarchy()
        self._detect_api_endpoints()
        self._detect_db_entities()
        self._detect_config_entries()

        result = {
            "summary": self._summary(),
            "symbol_index": self._symbols,
            "type_index": self._types,
            "import_graph": self._imports,
            "dependency_graph": self._dependencies,
            "module_graph": self._modules,
            "call_graph": self._calls,
            "class_hierarchy": self._class_hierarchy,
            "api_graph": self._api_endpoints,
            "database_graph": self._db_entities,
            "configuration_graph": self._config_entries,
        }

        bus.publish("RepositoryAnalyzed", {
            "root": str(self.root),
            "symbols": len(self._symbols),
            "modules": len(self._modules),
        })

        return result

    def _reset(self):
        self._ast_cache.clear()
        self._symbols.clear()
        self._types.clear()
        self._imports.clear()
        self._dependencies.clear()
        self._modules.clear()
        self._calls.clear()
        self._class_hierarchy.clear()
        self._api_endpoints.clear()
        self._db_entities.clear()
        self._config_entries = {}

    def _collect_python_files(self) -> list:
        files = []
        for f in self.root.rglob("*.py"):
            if any(part in EXCLUDE_DIRS for part in f.parts):
                continue
            files.append(f)
        return files

    def _collect_js_files(self) -> list:
        files = []
        for f in self.root.rglob("*.js"):
            if any(part in EXCLUDE_DIRS for part in f.parts):
                continue
            files.append(f)
        for f in self.root.rglob("*.ts"):
            if any(part in EXCLUDE_DIRS for part in f.parts):
                continue
            files.append(f)
        return files

    def _module_name(self, filepath: Path) -> str:
        rel = filepath.relative_to(self.root)
        return str(rel).replace("\\", "/").replace(".py", "").replace(".js", "").replace(".ts", "")

    def _analyze_python(self, filepath: Path):
        module_name = self._module_name(filepath)
        rel = str(filepath.relative_to(self.root)).replace("\\", "/")

        try:
            source = filepath.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except Exception:
            return

        self._ast_cache[module_name] = tree

        imports = []
        classes = []
        functions = []
        type_hints = {}
        calls = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
            elif isinstance(node, ast.ClassDef):
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        bases.append(self._attr_name(base))
                classes.append({
                    "name": node.name,
                    "bases": bases,
                    "line": node.lineno,
                    "methods": [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))],
                })

                self._symbols[f"{module_name}.{node.name}"] = {
                    "type": "class",
                    "module": module_name,
                    "file": rel,
                    "line": node.lineno,
                    "bases": bases,
                    "methods": [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))],
                }

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                params = []
                for arg in node.args.args:
                    param = {"name": arg.arg, "type": None}
                    if arg.annotation:
                        param["type"] = self._annotation_name(arg.annotation)
                        type_hints[arg.arg] = param["type"]
                    params.append(param)

                return_type = None
                if node.returns:
                    return_type = self._annotation_name(node.returns)

                functions.append({
                    "name": node.name,
                    "line": node.lineno,
                    "params": params,
                    "return_type": return_type,
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                })

                self._symbols[f"{module_name}.{node.name}"] = {
                    "type": "function",
                    "module": module_name,
                    "file": rel,
                    "line": node.lineno,
                    "params": [p["name"] for p in params],
                    "return_type": return_type,
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                }

                if return_type:
                    self._types[f"{module_name}.{node.name}"] = {
                        "return_type": return_type,
                        "params": {p["name"]: p["type"] for p in params if p["type"]},
                    }

            elif isinstance(node, ast.Call):
                callee = None
                if isinstance(node.func, ast.Name):
                    callee = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    callee = self._attr_name(node.func)
                if callee:
                    calls.append(callee)

        self._imports[module_name] = imports
        self._dependencies[module_name] = list(set(imports))
        self._calls[module_name] = list(set(calls))

        self._modules[module_name] = {
            "path": rel,
            "language": "python",
            "classes": [c["name"] for c in classes],
            "functions": [f["name"] for f in functions],
            "imports": imports,
            "class_details": classes,
            "function_details": functions,
            "type_hints": type_hints,
            "line_count": source.count("\n") + 1,
        }

    def _analyze_javascript(self, filepath: Path):
        module_name = self._module_name(filepath)
        rel = str(filepath.relative_to(self.root)).replace("\\", "/")

        try:
            source = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return

        imports = []
        classes = []
        functions = []
        calls = []

        import_patterns = [
            r'import\s+.*?\s+from\s+["\']([^"\']+)["\']',
            r'import\s+["\']([^"\']+)["\']',
            r'require\(\s*["\']([^"\']+)["\']\s*\)',
        ]
        for pattern in import_patterns:
            for match in re.finditer(pattern, source):
                imports.append(match.group(1))

        class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?'
        for match in re.finditer(class_pattern, source):
            name = match.group(1)
            base = match.group(2) or ""
            classes.append({"name": name, "bases": [base] if base else [], "line": source[:match.start()].count("\n") + 1})
            self._symbols[f"{module_name}.{name}"] = {
                "type": "class",
                "module": module_name,
                "file": rel,
                "line": source[:match.start()].count("\n") + 1,
                "bases": [base] if base else [],
            }

        func_patterns = [
            r'function\s+(\w+)\s*\(',
            r'const\s+(\w+)\s*=\s*(?:async\s+)?\(',
            r'const\s+(\w+)\s*=\s*(?:async\s+)?function',
            r'(\w+)\s*(?::\s*\w+)?\s*=\s*(?:async\s+)?\(',
        ]
        for pattern in func_patterns:
            for match in re.finditer(pattern, source):
                name = match.group(1)
                if name not in [f["name"] for f in functions]:
                    line = source[:match.start()].count("\n") + 1
                    functions.append({"name": name, "line": line})
                    self._symbols[f"{module_name}.{name}"] = {
                        "type": "function",
                        "module": module_name,
                        "file": rel,
                        "line": line,
                    }

        call_pattern = r'(\w+(?:\.\w+)*)\s*\('
        for match in re.finditer(call_pattern, source):
            callee = match.group(1)
            if callee not in ("if", "for", "while", "switch", "return", "catch", "function", "const", "let", "var"):
                calls.append(callee)

        self._imports[module_name] = list(set(imports))
        self._dependencies[module_name] = list(set(imports))
        self._calls[module_name] = list(set(calls))

        lang = "typescript" if filepath.suffix == ".ts" else "javascript"
        self._modules[module_name] = {
            "path": rel,
            "language": lang,
            "classes": [c["name"] for c in classes],
            "functions": [f["name"] for f in functions],
            "imports": list(set(imports)),
            "class_details": classes,
            "function_details": functions,
            "line_count": source.count("\n") + 1,
        }

    def _build_class_hierarchy(self):
        for symbol_name, info in self._symbols.items():
            if info["type"] != "class":
                continue
            class_name = symbol_name.split(".")[-1]
            bases = info.get("bases", [])
            for base in bases:
                if base not in self._class_hierarchy:
                    self._class_hierarchy[base] = []
                self._class_hierarchy[base].append(class_name)

    def _detect_api_endpoints(self):
        for module_name, info in self._modules.items():
            if info["language"] != "python":
                continue
            filepath = self.root / info["path"]
            try:
                source = filepath.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for decorator in node.decorator_list:
                        dec_name = self._decorator_name(decorator)
                        if dec_name and any(kw in dec_name.lower() for kw in ["get", "post", "put", "delete", "patch", "route", "endpoint", "api"]):
                            self._api_endpoints.append({
                                "module": module_name,
                                "function": node.name,
                                "decorator": dec_name,
                                "file": info["path"],
                                "line": node.lineno,
                            })

        for module_name, info in self._modules.items():
            if info["language"] not in ("javascript", "typescript"):
                continue
            filepath = self.root / info["path"]
            try:
                source = filepath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            route_patterns = [
                r'(?:app|router|server)\.(get|post|put|delete|patch|use)\s*\(\s*["\']([^"\']+)["\']',
                r'(?:app|router|server)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\'].*?function\s+(\w+)',
            ]
            for pattern in route_patterns:
                for match in re.finditer(pattern, source, re.DOTALL):
                    method = match.group(1).upper()
                    path = match.group(2)
                    func_name = match.group(3) if match.lastindex >= 3 else "anonymous"
                    line = source[:match.start()].count("\n") + 1
                    self._api_endpoints.append({
                        "module": module_name,
                        "function": func_name,
                        "decorator": f"{method} {path}",
                        "file": info["path"],
                        "line": line,
                    })

    def _detect_db_entities(self):
        for module_name, info in self._modules.items():
            if info["language"] != "python":
                continue
            filepath = self.root / info["path"]
            try:
                source = filepath.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        base_name = self._annotation_name(base) if isinstance(base, (ast.Name, ast.Attribute)) else ""
                        if any(kw in base_name.lower() for kw in ["model", "db", "table", "entity", "schema", "document", "collection"]):
                            self._db_entities.append({
                                "module": module_name,
                                "class": node.name,
                                "base": base_name,
                                "file": info["path"],
                                "line": node.lineno,
                            })

            table_pattern = r'__tablename__\s*=\s*["\']([^"\']+)["\']'
            for match in re.finditer(table_pattern, source):
                self._db_entities.append({
                    "module": module_name,
                    "table": match.group(1),
                    "file": info["path"],
                })

        sql_files = list(self.root.rglob("*.sql"))
        for sf in sql_files:
            if any(part in EXCLUDE_DIRS for part in sf.parts):
                continue
            try:
                content = sf.read_text(encoding="utf-8", errors="replace")
                for match in re.finditer(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)', content, re.IGNORECASE):
                    self._db_entities.append({
                        "table": match.group(1),
                        "file": str(sf.relative_to(self.root)).replace("\\", "/"),
                    })
            except Exception:
                pass

    def _detect_config_entries(self):
        config_files = {
            ".env": "dotenv",
            ".env.example": "dotenv",
            "config.json": "json",
            "config.yaml": "yaml",
            "config.yml": "yaml",
            "settings.json": "json",
            "settings.yaml": "yaml",
            "docker-compose.yml": "docker-compose",
            "docker-compose.yaml": "docker-compose",
            "Dockerfile": "dockerfile",
            "Makefile": "makefile",
            "pyproject.toml": "toml",
            "setup.cfg": "ini",
            "tsconfig.json": "json",
            "webpack.config.js": "js",
        }

        for filename, config_type in config_files.items():
            filepath = self.root / filename
            if filepath.exists():
                try:
                    content = filepath.read_text(encoding="utf-8", errors="replace")
                    self._config_entries[filename] = {
                        "type": config_type,
                        "path": filename,
                        "size": len(content),
                        "lines": content.count("\n") + 1,
                    }
                except Exception:
                    pass

        for f in self.root.rglob("*.env"):
            if any(part in EXCLUDE_DIRS for part in f.parts):
                continue
            name = f.name
            if name not in self._config_entries:
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                    self._config_entries[name] = {
                        "type": "dotenv",
                        "path": str(f.relative_to(self.root)).replace("\\", "/"),
                        "size": len(content),
                        "lines": content.count("\n") + 1,
                    }
                except Exception:
                    pass

    def _summary(self) -> dict:
        return {
            "total_modules": len(self._modules),
            "total_symbols": len(self._symbols),
            "total_classes": sum(1 for s in self._symbols.values() if s["type"] == "class"),
            "total_functions": sum(1 for s in self._symbols.values() if s["type"] == "function"),
            "total_imports": sum(len(v) for v in self._imports.values()),
            "total_calls": sum(len(v) for v in self._calls.values()),
            "api_endpoints": len(self._api_endpoints),
            "db_entities": len(self._db_entities),
            "config_files": len(self._config_entries),
        }

    def _annotation_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._attr_name(node)
        elif isinstance(node, ast.Subscript):
            return self._annotation_name(node.value)
        return ""

    def _attr_name(self, node) -> str:
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
        return ".".join(reversed(parts))

    def _decorator_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._attr_name(node)
        elif isinstance(node, ast.Call):
            return self._decorator_name(node.func)
        return ""


static_analyzer = StaticAnalyzer()
