import ast
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Optional


class ArchitectureAnalyzer:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._modules: dict[str, dict] = {}
        self._dependencies: dict[str, list[str]] = {}
        self._coupling: dict[str, int] = defaultdict(int)
        self._complexity: dict[str, int] = {}
        self._legacy: list[dict] = []
        self._hotspots: list[dict] = []

    def analyze(self) -> dict:
        self._modules.clear()
        self._dependencies.clear()
        self._coupling.clear()
        self._complexity.clear()
        self._legacy.clear()
        self._hotspots.clear()

        self._scan_python_files()
        self._identify_bottlenecks()
        self._identify_legacy()
        self._identify_hotspots()

        return {
            "modules": self._modules,
            "dependencies": self._dependencies,
            "coupling": dict(self._coupling),
            "complexity": self._complexity,
            "bottlenecks": self._bottlenecks,
            "legacy_modules": self._legacy,
            "risk_hotspots": self._hotspots,
            "summary": self._summary(),
        }

    def _scan_python_files(self):
        exclude = {"venv", "__pycache__", ".git", "node_modules", "assets"}
        py_files = []
        for f in self.root.rglob("*.py"):
            if any(part in exclude for part in f.parts):
                continue
            py_files.append(f)

        for filepath in py_files:
            rel = filepath.relative_to(self.root)
            module_name = str(rel).replace("\\", "/").replace(".py", "")

            try:
                source = filepath.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)
            except Exception:
                continue

            lines = source.count("\n")
            imports = []
            classes = []
            functions = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions.append(node.name)

            self._modules[module_name] = {
                "path": str(rel),
                "lines": lines,
                "classes": classes,
                "functions": functions,
                "imports": imports,
            }

            self._dependencies[module_name] = imports
            for imp in imports:
                self._coupling[imp] += 1

            complexity = len(classes) * 2 + len(functions) + lines // 50
            self._complexity[module_name] = complexity

    def _identify_bottlenecks(self):
        self._bottlenecks = []
        for module, deps in self._dependencies.items():
            if len(deps) > 15:
                self._bottlenecks.append({
                    "module": module,
                    "dependency_count": len(deps),
                    "severity": "high",
                })
            elif len(deps) > 10:
                self._bottlenecks.append({
                    "module": module,
                    "dependency_count": len(deps),
                    "severity": "medium",
                })

        for imp, count in sorted(self._coupling.items(), key=lambda x: -x[1]):
            if count > 8:
                self._bottlenecks.append({
                    "module": imp,
                    "imported_by_count": count,
                    "severity": "high" if count > 12 else "medium",
                    "type": "highly_coupled",
                })

    def _identify_legacy(self):
        for module, info in self._modules.items():
            warnings = []
            if info["lines"] > 300:
                warnings.append("large_file")
            if len(info["functions"]) > 20:
                warnings.append("too_many_functions")
            if not info["classes"] and info["lines"] > 100:
                warnings.append("procedural_style")

            if warnings:
                self._legacy.append({
                    "module": module,
                    "warnings": warnings,
                    "lines": info["lines"],
                })

    def _identify_hotspots(self):
        for module, complexity in sorted(self._complexity.items(), key=lambda x: -x[1])[:10]:
            info = self._modules.get(module, {})
            if complexity > 20:
                self._hotspots.append({
                    "module": module,
                    "complexity": complexity,
                    "lines": info.get("lines", 0),
                    "risk": "high" if complexity > 40 else "medium",
                })

    def _summary(self) -> dict:
        total_lines = sum(m["lines"] for m in self._modules.values())
        total_classes = sum(len(m["classes"]) for m in self._modules.values())
        total_functions = sum(len(m["functions"]) for m in self._modules.values())

        return {
            "total_modules": len(self._modules),
            "total_lines": total_lines,
            "total_classes": total_classes,
            "total_functions": total_functions,
            "avg_complexity": round(sum(self._complexity.values()) / max(len(self._complexity), 1), 1),
            "bottleneck_count": len(self._bottlenecks),
            "legacy_count": len(self._legacy),
            "hotspot_count": len(self._hotspots),
        }


architecture_analyzer = ArchitectureAnalyzer()
