import ast
import re
from pathlib import Path
from typing import Optional
from collections import defaultdict

from core.event_bus import bus
from ai.repo.languages import EXCLUDE_DIRS


class CodeReviewer:
    """Reviews code for architecture, SOLID, DRY, performance, security,
    scalability, multi-tenancy, offline capability, and error handling."""

    def __init__(self, root: str = "."):
        self.root = Path(root).resolve()

    def review_file(self, filepath: str) -> dict:
        """Review a single file."""
        full_path = self.root / filepath
        if not full_path.exists():
            return {"error": f"File not found: {filepath}"}

        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {"error": str(e)}

        ext = full_path.suffix.lower()
        if ext == ".py":
            return self._review_python(filepath, content)
        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            return self._review_javascript(filepath, content)
        else:
            return self._review_generic(filepath, content)

    def review_repository(self) -> dict:
        """Review all source files in the repository."""
        results = []
        for filepath in self._walk_source_files():
            rel = str(filepath.relative_to(self.root)).replace("\\", "/")
            review = self.review_file(rel)
            if "error" not in review:
                results.append(review)

        summary = self._aggregate_reviews(results)

        bus.publish("CodeReviewCompleted", {
            "root": str(self.root),
            "files_reviewed": len(results),
            "total_issues": summary["total_issues"],
        })

        return {"files": results, "summary": summary}

    def _review_python(self, filepath: str, content: str) -> dict:
        issues = []
        metrics = {}

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return {"file": filepath, "error": f"Syntax error: {e}", "issues": []}

        lines = content.split("\n")
        metrics["line_count"] = len(lines)

        classes = []
        functions = []
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node)
                issues.extend(self._check_solid_class(filepath, node))
                issues.extend(self._check_dry_class(filepath, node, content))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node)
                issues.extend(self._check_function_complexity(filepath, node))
                issues.extend(self._check_error_handling(filepath, node))
                issues.extend(self._check_security(filepath, node, content))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        metrics["class_count"] = len(classes)
        metrics["function_count"] = len(functions)
        metrics["import_count"] = len(imports)

        issues.extend(self._check_architecture(filepath, content, classes, functions))
        issues.extend(self._check_performance(filepath, content, tree))
        issues.extend(self._check_scalability(filepath, content))
        issues.extend(self._check_multi_tenancy(filepath, content))
        issues.extend(self._check_offline_capability(filepath, content))

        issues.sort(key=lambda x: x.get("line", 0))

        return {
            "file": filepath,
            "language": "python",
            "metrics": metrics,
            "issues": issues,
            "issue_count": len(issues),
            "quality_score": self._calculate_quality_score(issues, metrics),
        }

    def _review_javascript(self, filepath: str, content: str) -> dict:
        issues = []
        metrics = {}

        lines = content.split("\n")
        metrics["line_count"] = len(lines)

        if any(kw in content for kw in ["eval(", "innerHTML", "document.write"]):
            issues.append({
                "file": filepath,
                "category": "security",
                "severity": "high",
                "message": "Potentially dangerous function (eval/innerHTML/document.write) detected",
                "line": self._find_line(content, ["eval(", "innerHTML", "document.write"]),
            })

        if "var " in content and "let " not in content and "const " not in content:
            issues.append({
                "file": filepath,
                "category": "architecture",
                "severity": "low",
                "message": "Uses 'var' instead of 'let'/'const' — consider modern variable declarations",
                "line": 1,
            })

        if re.search(r'password\s*[:=]\s*["\'][^"\']+["\']', content, re.IGNORECASE):
            issues.append({
                "file": filepath,
                "category": "security",
                "severity": "critical",
                "message": "Hardcoded password detected",
                "line": self._find_line(content, ["password"]),
            })

        if "TODO" in content or "FIXME" in content:
            issues.append({
                "file": filepath,
                "category": "architecture",
                "severity": "low",
                "message": "Contains TODO/FIXME comments",
                "line": self._find_line(content, ["TODO", "FIXME"]),
            })

        long_lines = [(i + 1, line) for i, line in enumerate(lines) if len(line) > 120]
        for line_num, line in long_lines:
            issues.append({
                "file": filepath,
                "category": "architecture",
                "severity": "low",
                "message": f"Line too long ({len(line)} chars)",
                "line": line_num,
            })

        func_count = len(re.findall(r'function\s+\w+|=>\s*{|const\s+\w+\s*=\s*(?:async\s+)?\(', content))
        class_count = len(re.findall(r'class\s+\w+', content))
        metrics["function_count"] = func_count
        metrics["class_count"] = class_count

        issues.extend(self._check_scalability(filepath, content))
        issues.extend(self._check_multi_tenancy(filepath, content))

        issues.sort(key=lambda x: x.get("line", 0))

        return {
            "file": filepath,
            "language": "javascript",
            "metrics": metrics,
            "issues": issues,
            "issue_count": len(issues),
            "quality_score": self._calculate_quality_score(issues, metrics),
        }

    def _review_generic(self, filepath: str, content: str) -> dict:
        issues = []
        lines = content.split("\n")

        if re.search(r'password\s*=\s*\S+', content, re.IGNORECASE):
            issues.append({
                "file": filepath,
                "category": "security",
                "severity": "high",
                "message": "Possible hardcoded password",
                "line": self._find_line(content, ["password"]),
            })

        for i, line in enumerate(lines):
            if len(line) > 200:
                issues.append({
                    "file": filepath,
                    "category": "architecture",
                    "severity": "low",
                    "message": f"Line too long ({len(line)} chars)",
                    "line": i + 1,
                })

        return {
            "file": filepath,
            "language": "generic",
            "metrics": {"line_count": len(lines)},
            "issues": issues,
            "issue_count": len(issues),
            "quality_score": self._calculate_quality_score(issues, {"line_count": len(lines)}),
        }

    def _check_solid_class(self, filepath: str, node: ast.ClassDef) -> list:
        issues = []

        method_count = sum(1 for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
        if method_count > 20:
            issues.append({
                "file": filepath,
                "category": "SOLID",
                "severity": "medium",
                "message": f"Class '{node.name}' has {method_count} methods — possible SRP violation",
                "line": node.lineno,
            })

        bases = [self._get_name(b) for b in node.bases]
        if len(bases) > 3:
            issues.append({
                "file": filepath,
                "category": "SOLID",
                "severity": "medium",
                "message": f"Class '{node.name}' inherits from {len(bases)} classes — possible ISP violation",
                "line": node.lineno,
            })

        public_methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("_")]
        if len(public_methods) > 10:
            issues.append({
                "file": filepath,
                "category": "SOLID",
                "severity": "low",
                "message": f"Class '{node.name}' exposes {len(public_methods)} public methods — consider interface segregation",
                "line": node.lineno,
            })

        return issues

    def _check_dry_class(self, filepath: str, node: ast.ClassDef, content: str) -> list:
        issues = []

        method_bodies = []
        for n in node.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                try:
                    body = ast.unparse(n) if hasattr(ast, "unparse") else ""
                    method_bodies.append((n.name, body, n.lineno))
                except Exception:
                    pass

        for i, (name1, body1, line1) in enumerate(method_bodies):
            for name2, body2, line2 in method_bodies[i + 1:]:
                if name1 != name2 and body1 and body2:
                    similarity = self._similarity(body1, body2)
                    if similarity > 0.8:
                        issues.append({
                            "file": filepath,
                            "category": "DRY",
                            "severity": "medium",
                            "message": f"Methods '{name1}' and '{name2}' are {similarity:.0%} similar — possible duplication",
                            "line": line1,
                        })

        return issues

    def _check_function_complexity(self, filepath: str, node) -> list:
        issues = []

        body_lines = 0
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler,
                                   ast.With, ast.AsyncFor)):
                body_lines += 1

        if body_lines > 10:
            issues.append({
                "file": filepath,
                "category": "complexity",
                "severity": "medium",
                "message": f"Function '{node.name}' has cyclomatic complexity ~{body_lines} — consider refactoring",
                "line": node.lineno,
            })

        param_count = len(node.args.args)
        if param_count > 5:
            issues.append({
                "file": filepath,
                "category": "complexity",
                "severity": "low",
                "message": f"Function '{node.name}' has {param_count} parameters — consider using a data class",
                "line": node.lineno,
            })

        return issues

    def _check_error_handling(self, filepath: str, node) -> list:
        issues = []

        has_try = False
        bare_except = False

        for child in ast.walk(node):
            if isinstance(child, ast.Try):
                has_try = True
            if isinstance(child, ast.ExceptHandler):
                if child.type is None:
                    bare_except = True

        if bare_except:
            issues.append({
                "file": filepath,
                "category": "error_handling",
                "severity": "medium",
                "message": f"Function '{node.name}' uses bare 'except:' — catch specific exceptions",
                "line": node.lineno,
            })

        return issues

    def _check_security(self, filepath: str, node, content: str) -> list:
        issues = []

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func_name = self._get_name(child.func)
                if func_name == "eval":
                    issues.append({
                        "file": filepath,
                        "category": "security",
                        "severity": "critical",
                        "message": "Use of eval() is dangerous",
                        "line": child.lineno,
                    })
                elif func_name == "exec":
                    issues.append({
                        "file": filepath,
                        "category": "security",
                        "severity": "high",
                        "message": "Use of exec() is dangerous",
                        "line": child.lineno,
                    })
                elif func_name == "subprocess.call" and child.args:
                    if isinstance(child.args[0], ast.Constant) and "shell=True" in str(child.args):
                        issues.append({
                            "file": filepath,
                            "category": "security",
                            "severity": "high",
                            "message": "subprocess with shell=True can be dangerous",
                            "line": child.lineno,
                        })

        return issues

    def _check_architecture(self, filepath: str, content: str, classes: list, functions: list) -> list:
        issues = []

        if len(content) > 10000:
            issues.append({
                "file": filepath,
                "category": "architecture",
                "severity": "medium",
                "message": "File is very large — consider splitting into modules",
                "line": 1,
            })

        if len(functions) > 30:
            issues.append({
                "file": filepath,
                "category": "architecture",
                "severity": "low",
                "message": f"File has {len(functions)} functions — consider splitting",
                "line": 1,
            })

        return issues

    def _check_performance(self, filepath: str, content: str, tree: ast.AST) -> list:
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.AsyncFor)):
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        func_name = self._get_name(child.func)
                        if func_name in ("append", "extend") and isinstance(child.func, ast.Attribute):
                            if isinstance(child.func.value, ast.Name):
                                pass

            if isinstance(node, ast.Compare):
                if isinstance(node.ops[0], ast.In) and isinstance(node.left, ast.Name):
                    pass

        if re.search(r'for\s+\w+\s+in\s+range\s*\(\s*len\s*\(', content):
            issues.append({
                "file": filepath,
                "category": "performance",
                "severity": "low",
                "message": "Using range(len()) pattern — consider enumerate() or direct iteration",
                "line": self._find_line(content, ["for", "range", "len"]),
            })

        if "SELECT *" in content:
            issues.append({
                "file": filepath,
                "category": "performance",
                "severity": "medium",
                "message": "SELECT * in SQL — specify columns for better performance",
                "line": self._find_line(content, ["SELECT *"]),
            })

        return issues

    def _check_scalability(self, filepath: str, content: str) -> list:
        issues = []

        if "global " in content:
            issues.append({
                "file": filepath,
                "category": "scalability",
                "severity": "medium",
                "message": "Use of global variables limits horizontal scalability",
                "line": self._find_line(content, ["global "]),
            })

        if re.search(r'time\.sleep\s*\(\s*\d+\s*\)', content):
            issues.append({
                "file": filepath,
                "category": "scalability",
                "severity": "low",
                "message": "Blocking sleep() call — consider async alternatives",
                "line": self._find_line(content, ["time.sleep"]),
            })

        return issues

    def _check_multi_tenancy(self, filepath: str, content: str) -> list:
        issues = []

        if re.search(r'(user_id|tenant_id|org_id)', content, re.IGNORECASE):
            if not re.search(r'(tenant_id|org_id)', content, re.IGNORECASE):
                issues.append({
                    "file": filepath,
                    "category": "multi_tenancy",
                    "severity": "low",
                    "message": "Uses user_id but no tenant_id — may not support multi-tenancy",
                    "line": 1,
                })

        return issues

    def _check_offline_capability(self, filepath: str, content: str) -> list:
        issues = []

        if re.search(r'requests\.get|fetch\s*\(|axios\.', content):
            if not re.search(r'(retry|fallback|cache|offline)', content, re.IGNORECASE):
                issues.append({
                    "file": filepath,
                    "category": "offline_capability",
                    "severity": "low",
                    "message": "Network call without retry/fallback/cache — no offline support",
                    "line": 1,
                })

        return issues

    def _calculate_quality_score(self, issues: list, metrics: dict) -> int:
        penalties = {"critical": 20, "high": 10, "medium": 5, "low": 1}
        total_penalty = sum(penalties.get(i.get("severity", "low"), 1) for i in issues)
        line_count = max(metrics.get("line_count", 1), 1)
        score = max(0, 100 - (total_penalty * 100 // (line_count + total_penalty)))
        return score

    def _similarity(self, a: str, b: str) -> float:
        if not a or not b:
            return 0
        set_a = set(a.split())
        set_b = set(b.split())
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union) if union else 0

    def _find_line(self, content: str, keywords: list) -> int:
        for i, line in enumerate(content.split("\n"), 1):
            for kw in keywords:
                if kw in line:
                    return i
        return 0

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

    def _walk_source_files(self):
        source_exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cs", ".go", ".rs", ".php"}
        for filepath in self.root.rglob("*"):
            if not filepath.is_file():
                continue
            if any(part in EXCLUDE_DIRS for part in filepath.parts):
                continue
            if filepath.suffix.lower() in source_exts:
                yield filepath

    def _aggregate_reviews(self, reviews: list) -> dict:
        total_issues = sum(r["issue_count"] for r in reviews)
        by_category = defaultdict(int)
        by_severity = defaultdict(int)

        for review in reviews:
            for issue in review.get("issues", []):
                by_category[issue.get("category", "unknown")] += 1
                by_severity[issue.get("severity", "low")] += 1

        avg_quality = sum(r.get("quality_score", 0) for r in reviews) / max(len(reviews), 1)

        return {
            "files_reviewed": len(reviews),
            "total_issues": total_issues,
            "by_category": dict(by_category),
            "by_severity": dict(by_severity),
            "average_quality_score": round(avg_quality, 1),
        }


code_reviewer = CodeReviewer()
