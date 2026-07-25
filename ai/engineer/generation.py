import ast
import re
import json
from pathlib import Path
from typing import Optional
from collections import defaultdict

from core.event_bus import bus
from ai.repo.languages import EXCLUDE_DIRS


class CodeGenerator:
    """Generates unit tests, integration tests, documentation,
    refactoring plans, and migration plans."""

    def __init__(self, root: str = "."):
        self.root = Path(root).resolve()

    def generate_unit_tests(self, file_path: str) -> dict:
        """Generate unit test stubs for all functions in a Python file."""
        full_path = self.root / file_path
        if not full_path.exists():
            return {"error": f"File not found: {file_path}"}

        try:
            source = full_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except Exception as e:
            return {"error": str(e)}

        functions = []
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_") or node.name in ("__init__",):
                    params = []
                    for arg in node.args.args:
                        if arg.arg != "self":
                            params.append(arg.arg)
                    functions.append({
                        "name": node.name,
                        "params": params,
                        "line": node.lineno,
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                    })
            elif isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        params = []
                        for arg in item.args.args:
                            if arg.arg != "self":
                                params.append(arg.arg)
                        methods.append({
                            "name": item.name,
                            "params": params,
                            "is_async": isinstance(item, ast.AsyncFunctionDef),
                        })
                classes.append({"name": node.name, "methods": methods, "line": node.lineno})

        test_code = self._build_unit_test_code(file_path, functions, classes)

        bus.publish("UnitTestsGenerated", {"file": file_path, "functions": len(functions), "classes": len(classes)})

        return {
            "source_file": file_path,
            "functions": functions,
            "classes": classes,
            "test_code": test_code,
            "test_file": f"test_{Path(file_path).stem}.py",
        }

    def _build_unit_test_code(self, file_path: str, functions: list, classes: list) -> str:
        module_name = file_path.replace("/", ".").replace(".py", "")
        lines = [
            f"import unittest",
            f"from unittest.mock import Mock, patch, MagicMock",
            f"from {module_name} import *",
            "",
            "",
        ]

        for cls in classes:
            lines.append(f"class Test{cls['name']}(unittest.TestCase):")
            if not cls["methods"]:
                lines.append("    pass")
            for method in cls["methods"]:
                test_name = f"test_{method['name']}"
                lines.append(f"    def {test_name}(self):")
                params = ", ".join(["Mock()"] * len(method["params"]))
                if method["is_async"]:
                    lines.append(f"        # TODO: Test async method {method['name']}")
                    lines.append(f"        import asyncio")
                    lines.append(f"        instance = {cls['name']}()")
                    lines.append(f"        result = asyncio.get_event_loop().run_until_complete(instance.{method['name']}({params}))")
                else:
                    lines.append(f"        instance = {cls['name']}()")
                    lines.append(f"        result = instance.{method['name']}({params})")
                    lines.append(f"        self.assertIsNotNone(result)")
                lines.append("")
            lines.append("")

        if functions:
            lines.append(f"class TestModuleFunctions(unittest.TestCase):")
            for func in functions:
                test_name = f"test_{func['name']}"
                lines.append(f"    def {test_name}(self):")
                params = ", ".join(["Mock()"] * len(func["params"]))
                if func["is_async"]:
                    lines.append(f"        import asyncio")
                    lines.append(f"        result = asyncio.get_event_loop().run_until_complete({func['name']}({params}))")
                else:
                    lines.append(f"        result = {func['name']}({params})")
                    lines.append(f"        self.assertIsNotNone(result)")
                lines.append("")
            lines.append("")

        lines.append("if __name__ == '__main__':")
        lines.append("    unittest.main()")
        lines.append("")

        return "\n".join(lines)

    def generate_integration_tests(self, module_path: str) -> dict:
        """Generate integration test scaffolding for a module."""
        full_path = self.root / module_path
        if not full_path.exists():
            return {"error": f"Module not found: {module_path}"}

        module_name = module_path.replace("/", ".").replace(".py", "")

        test_code = f"""import unittest
from unittest.mock import Mock, patch
from {module_name} import *


class TestIntegration(unittest.TestCase):
    \"\"\"Integration tests for {module_path}.\"\"\"

    def setUp(self):
        \"\"\"Set up test fixtures.\"\"\"
        pass

    def tearDown(self):
        \"\"\"Clean up after tests.\"\"\"
        pass

    def test_module_imports(self):
        \"\"\"Verify module can be imported.\"\"\"
        import {module_name}
        self.assertTrue(hasattr({module_name}, '__name__'))

    def test_module_workflow(self):
        \"\"\"Test end-to-end module workflow.\"\"\"
        # TODO: Implement integration test
        pass

    def test_error_handling(self):
        \"\"\"Test error handling across module.\"\"\"
        # TODO: Test error scenarios
        pass

    def test_data_flow(self):
        \"\"\"Test data flow through module.\"\"\"
        # TODO: Verify data integrity
        pass


if __name__ == '__main__':
    unittest.main()
"""

        return {
            "source_module": module_path,
            "test_code": test_code,
            "test_file": f"test_integration_{Path(module_path).stem}.py",
        }

    def generate_documentation(self, file_path: str) -> dict:
        """Generate documentation for a source file."""
        full_path = self.root / file_path
        if not full_path.exists():
            return {"error": f"File not found: {file_path}"}

        try:
            source = full_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except Exception as e:
            return {"error": str(e)}

        doc_parts = [f"# Documentation: {file_path}", ""]

        module_doc = ast.get_docstring(tree)
        if module_doc:
            doc_parts.append(f"## Module Description\n\n{module_doc}\n")

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                doc_parts.append(f"## Class: {node.name}\n")

                class_doc = ast.get_docstring(node)
                if class_doc:
                    doc_parts.append(f"{class_doc}\n")

                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        bases.append(self._attr_name(base))
                if bases:
                    doc_parts.append(f"**Inherits from:** {', '.join(bases)}\n")

                doc_parts.append("### Methods\n")
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        params = [arg.arg for arg in item.args.args if arg.arg != "self"]
                        return_type = ""
                        if item.returns:
                            return_type = f" -> {self._annotation_name(item.returns)}"

                        method_doc = ast.get_docstring(item)
                        doc_parts.append(f"- **{item.name}({', '.join(params)}){return_type}**")
                        if method_doc:
                            doc_parts.append(f"  - {method_doc}")
                        doc_parts.append("")

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_") and node.name != "__init__":
                    continue

                params = [arg.arg for arg in node.args.args]
                return_type = ""
                if node.returns:
                    return_type = f" -> {self._annotation_name(node.returns)}"

                func_doc = ast.get_docstring(node)
                doc_parts.append(f"## Function: {node.name}({', '.join(params)}){return_type}\n")
                if func_doc:
                    doc_parts.append(f"{func_doc}\n")
                doc_parts.append(f"**Location:** {file_path}:{node.lineno}\n")

        doc_text = "\n".join(doc_parts)

        bus.publish("DocumentationGenerated", {"file": file_path, "length": len(doc_text)})

        return {
            "source_file": file_path,
            "documentation": doc_text,
            "doc_file": f"{Path(file_path).stem}.md",
        }

    def generate_refactoring_plan(self, file_path: str) -> dict:
        """Generate a refactoring plan for a file."""
        full_path = self.root / file_path
        if not full_path.exists():
            return {"error": f"File not found: {file_path}"}

        try:
            source = full_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except Exception as e:
            return {"error": str(e)}

        plan = []
        lines = source.split("\n")
        line_count = len(lines)

        if line_count > 300:
            plan.append({
                "priority": "high",
                "category": "size",
                "description": f"File has {line_count} lines — split into smaller modules",
                "effort": "high",
            })

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                method_count = sum(1 for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
                if method_count > 15:
                    plan.append({
                        "priority": "high",
                        "category": "SRP",
                        "description": f"Class '{node.name}' has {method_count} methods — split into smaller classes",
                        "effort": "high",
                        "line": node.lineno,
                    })

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = sum(1 for child in ast.walk(node)
                                 if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)))
                if complexity > 8:
                    plan.append({
                        "priority": "medium",
                        "category": "complexity",
                        "description": f"Function '{node.name}' has complexity {complexity} — extract sub-functions",
                        "effort": "medium",
                        "line": node.lineno,
                    })

                param_count = len(node.args.args)
                if param_count > 5:
                    plan.append({
                        "priority": "low",
                        "category": "parameters",
                        "description": f"Function '{node.name}' has {param_count} parameters — use parameter object",
                        "effort": "low",
                        "line": node.lineno,
                    })

        for match in re.finditer(r'except\s*:\s*pass', source):
            line = source[:match.start()].count("\n") + 1
            plan.append({
                "priority": "medium",
                "category": "error_handling",
                "description": "Bare except with pass — add proper error handling",
                "effort": "low",
                "line": line,
            })

        for match in re.finditer(r'except\s+Exception\s*:\s*pass', source):
            line = source[:match.start()].count("\n") + 1
            plan.append({
                "priority": "medium",
                "category": "error_handling",
                "description": "Catching Exception and passing — log or re-raise",
                "effort": "low",
                "line": line,
            })

        plan.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x["priority"], 3))

        return {
            "source_file": file_path,
            "line_count": line_count,
            "refactoring_plan": plan,
            "total_recommendations": len(plan),
        }

    def generate_migration_plan(self, from_framework: str, to_framework: str) -> dict:
        """Generate a migration plan between frameworks."""
        phases = [
            {
                "phase": 1,
                "name": "Assessment",
                "tasks": [
                    f"Audit all {from_framework} components and dependencies",
                    "Map {from_framework} patterns to {to_framework} equivalents",
                    "Identify breaking changes and risks",
                    "Create test baseline for existing functionality",
                ],
            },
            {
                "phase": 2,
                "name": "Preparation",
                "tasks": [
                    f"Install {to_framework} alongside {from_framework}",
                    "Set up shared configuration and routing",
                    "Create compatibility layer for gradual migration",
                    "Update build system and dependencies",
                ],
            },
            {
                "phase": 3,
                "name": "Migration",
                "tasks": [
                    "Migrate entry points and routing first",
                    "Migrate controllers/handlers one by one",
                    "Migrate middleware and interceptors",
                    "Migrate models and data access layer",
                    "Migrate views/templates",
                    "Run tests after each component migration",
                ],
            },
            {
                "phase": 4,
                "name": "Validation",
                "tasks": [
                    "Run full test suite",
                    "Perform integration testing",
                    "Verify performance benchmarks",
                    "Check for deprecated API usage",
                    "Security audit",
                ],
            },
            {
                "phase": 5,
                "name": "Cleanup",
                "tasks": [
                    f"Remove {from_framework} dependencies",
                    "Remove compatibility layer",
                    "Update documentation",
                    "Update CI/CD pipelines",
                    "Final review and sign-off",
                ],
            },
        ]

        return {
            "from": from_framework,
            "to": to_framework,
            "phases": phases,
            "estimated_effort": "Large migration — plan 2-4 weeks minimum",
            "risk_level": "high",
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


code_generator = CodeGenerator()
