"""Build • Test • Fix • Retry Loop — automated iterative code development.
Generates code, builds it, detects errors, root-causes, fixes, and retries."""

import re
import subprocess
import time
from pathlib import Path
from typing import Optional

from core.event_bus import bus
from logs.logger import write_log


class BuildTestFixLoop:
    """Automated build-test-fix-retry loop for iterative code development.
    Supports npm, yarn, pnpm, Maven, Gradle, and Python projects."""

    def __init__(self, max_retries: int = 5):
        self.max_retries = max_retries

    def run(self, project_path: str, build_cmd: str = None, test_cmd: str = None,
            language: str = None) -> dict:
        """Run the full build-test-fix-retry loop.

        Args:
            project_path: Root directory of the project
            build_cmd: Build command (auto-detected if None)
            test_cmd: Test command (auto-detected if None)
            language: Project language (auto-detected if None)

        Returns:
            dict with final status, attempts, and logs
        """
        root = Path(project_path).resolve()
        if not root.exists():
            return {"status": "error", "error": f"Project path not found: {root}"}

        if language is None:
            language = self._detect_language(root)

        if build_cmd is None:
            build_cmd = self._detect_build_cmd(root, language)

        if test_cmd is None:
            test_cmd = self._detect_test_cmd(root, language)

        bus.publish("BuildTestFixStarted", {
            "project": str(root),
            "language": language,
            "build_cmd": build_cmd,
            "test_cmd": test_cmd,
            "max_retries": self.max_retries,
        })

        attempts = []
        current_code = ""
        fixed = False

        for attempt in range(1, self.max_retries + 1):
            write_log("BUILD_LOOP", f"Attempt {attempt}/{self.max_retries}")

            # ── Step 1: Build ──
            build_result = self._execute(build_cmd, root)
            attempts.append({
                "attempt": attempt,
                "phase": "build",
                "exit_code": build_result["exit_code"],
                "stdout": build_result["stdout"][:2000],
                "stderr": build_result["stderr"][:2000],
            })

            bus.publish("BuildTestFixBuild", {"attempt": attempt, "success": build_result["exit_code"] == 0})

            if build_result["exit_code"] == 0:
                # ── Step 2: Test ──
                test_result = self._execute(test_cmd, root)
                attempts[-1]["test"] = {
                    "exit_code": test_result["exit_code"],
                    "stdout": test_result["stdout"][:2000],
                    "stderr": test_result["stderr"][:2000],
                }

                bus.publish("BuildTestFixTest", {"attempt": attempt, "success": test_result["exit_code"] == 0})

                if test_result["exit_code"] == 0:
                    fixed = True
                    break

                # Test failed — analyze and fix
                error_output = test_result["stderr"] or test_result["stdout"]
                error_analysis = self._analyze_error(error_output, root, language)
                fix = self._generate_fix(error_analysis, root, language)
                self._apply_fix(fix, root)
                current_code = fix
            else:
                # Build failed — analyze and fix
                error_output = build_result["stderr"] or build_result["stdout"]
                error_analysis = self._analyze_error(error_output, root, language)
                fix = self._generate_fix(error_analysis, root, language)
                self._apply_fix(fix, root)
                current_code = fix

            write_log("BUILD_LOOP", f"Attempt {attempt} failed, retrying...")

        status = "passed" if fixed else "failed"
        duration_ms = sum(a.get("test", a).get("exit_code", 0) for a in attempts)  # rough

        bus.publish("BuildTestFixCompleted", {
            "project": str(root),
            "status": status,
            "attempts": len(attempts),
        })

        return {
            "status": status,
            "attempts": len(attempts),
            "max_retries": self.max_retries,
            "language": language,
            "build_cmd": build_cmd,
            "test_cmd": test_cmd,
            "logs": attempts,
            "final_fix": current_code[:500] if current_code else "",
        }

    def _detect_language(self, root: Path) -> str:
        """Detect project language from files."""
        if (root / "package.json").exists():
            pkg = (root / "package.json").read_text(encoding="utf-8", errors="replace")
            if "react" in pkg.lower():
                return "react"
            return "node"
        if (root / "pom.xml").exists():
            return "maven"
        if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
            return "gradle"
        if (root / "requirements.txt").exists() or (root / "pyproject.toml").exists():
            return "python"
        if any(root.glob("*.py")):
            return "python"
        return "unknown"

    def _detect_build_cmd(self, root: Path, language: str) -> str:
        """Auto-detect build command based on project type."""
        if language == "node":
            pkg = root / "package.json"
            if pkg.exists():
                import json
                try:
                    data = json.loads(pkg.read_text())
                    if "build" in data.get("scripts", {}):
                        return "npm run build"
                except Exception:
                    pass
            return "npm run build"
        elif language == "react":
            return "npm run build"
        elif language == "maven":
            return "mvn compile"
        elif language == "gradle":
            if (root / "gradlew").exists():
                return "./gradlew build"
            return "gradle build"
        elif language == "python":
            if (root / "pyproject.toml").exists():
                return "python -m build"
            return "python -c \"import py_compile; [py_compile.compile(f, doraise=True) for f in __import__('pathlib').Path('.').rglob('*.py')]\""
        return "echo no_build_command"

    def _detect_test_cmd(self, root: Path, language: str) -> str:
        """Auto-detect test command based on project type."""
        if language in ("node", "react"):
            pkg = root / "package.json"
            if pkg.exists():
                import json
                try:
                    data = json.loads(pkg.read_text())
                    if "test" in data.get("scripts", {}):
                        return "npm test"
                except Exception:
                    pass
            return "npm test"
        elif language == "maven":
            return "mvn test"
        elif language == "gradle":
            if (root / "gradlew").exists():
                return "./gradlew test"
            return "gradle test"
        elif language == "python":
            if (root / "pytest.ini").exists() or (root / "pyproject.toml").exists():
                return "python -m pytest -v"
            return "python -m unittest discover"
        return "echo no_test_command"

    def _execute(self, cmd: str, cwd: Path, timeout: int = 120) -> dict:
        """Execute a shell command and return result."""
        try:
            if cmd.startswith("./"):
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True,
                    timeout=timeout, cwd=str(cwd),
                )
            else:
                result = subprocess.run(
                    cmd.split(), capture_output=True, text=True,
                    timeout=timeout, cwd=str(cwd),
                )
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        except subprocess.TimeoutExpired:
            return {"exit_code": -1, "stdout": "", "stderr": "Command timed out"}
        except Exception as e:
            return {"exit_code": -1, "stdout": "", "stderr": str(e)}

    def _analyze_error(self, error_output: str, root: Path, language: str) -> dict:
        """Analyze build/test error output to identify root cause."""
        analysis = {
            "raw_error": error_output[:3000],
            "language": language,
            "error_type": "unknown",
            "file": None,
            "line": None,
            "message": "",
        }

        # Python error patterns
        py_patterns = [
            (r"File \"(.+?)\", line (\d+).*?(\w+Error): (.+)", "python_exception"),
            (r"ModuleNotFoundError: No module named '(.+?)'", "missing_module"),
            (r"ImportError: (.+)", "import_error"),
            (r"SyntaxError: (.+?) \((.+?), line (\d+)\)", "syntax_error"),
            (r"IndentationError: (.+)", "indentation_error"),
            (r"AssertionError: (.+)", "assertion_error"),
            (r"TypeError: (.+)", "type_error"),
            (r"NameError: name '(.+?)' is not defined", "name_error"),
            (r"AttributeError: (.+)", "attribute_error"),
            (r"KeyError: (.+)", "key_error"),
        ]

        # Node/JS error patterns
        js_patterns = [
            (r"SyntaxError: (.+?)\n.*?at (.+?):(\d+):(\d+)", "js_syntax_error"),
            (r"TypeError: (.+?)\n.*?at (.+?):(\d+):(\d+)", "js_type_error"),
            (r"ReferenceError: (.+?) is not defined", "js_reference_error"),
            (r"Cannot find module '(.+?)'", "js_missing_module"),
            (r"Error: (.+?)\n.*?at (.+?):(\d+):(\d+)", "js_generic_error"),
        ]

        # Maven/Gradle patterns
        java_patterns = [
            (r"ERROR\].*?(.+?).java:\[(\d+),(\d+)\] (.+)", "java_compile_error"),
            (r"BUILD FAILURE", "maven_build_failure"),
            (r"FAILURE: Build failed with an exception", "gradle_build_failure"),
            (r"java.lang.(.+?Exception): (.+)", "java_exception"),
        ]

        all_patterns = py_patterns + js_patterns + java_patterns

        for pattern, error_type in all_patterns:
            match = re.search(pattern, error_output)
            if match:
                analysis["error_type"] = error_type
                groups = match.groups()
                if error_type.startswith("python"):
                    if len(groups) >= 4:
                        analysis["file"] = groups[0]
                        analysis["line"] = int(groups[1]) if groups[1].isdigit() else groups[1]
                        analysis["message"] = f"{groups[2]}: {groups[3]}"
                    elif len(groups) >= 1:
                        analysis["message"] = groups[0]
                elif error_type.startswith("js"):
                    if len(groups) >= 4:
                        analysis["message"] = groups[0]
                        analysis["file"] = groups[1]
                        analysis["line"] = groups[2]
                    elif len(groups) >= 1:
                        analysis["message"] = groups[0]
                elif error_type.startswith("java") or error_type.startswith("maven") or error_type.startswith("gradle"):
                    if len(groups) >= 4:
                        analysis["file"] = groups[0]
                        analysis["line"] = groups[1]
                        analysis["message"] = groups[3]
                    elif len(groups) >= 2:
                        analysis["message"] = f"{groups[0]}: {groups[1]}"
                    elif len(groups) >= 1:
                        analysis["message"] = groups[0]
                break

        # Try root cause analyzer if available
        try:
            from core.service_registry import registry
            if registry.has("ai_engineer"):
                ai_eng = registry.get("ai_engineer")
                rc = ai_eng.analyze_failure(
                    error=analysis["message"],
                    stack_trace=error_output[:2000],
                    file_path=analysis["file"],
                )
                analysis["root_cause"] = rc
        except Exception:
            pass

        return analysis

    def _generate_fix(self, analysis: dict, root: Path, language: str) -> str:
        """Generate a fix using the LLM based on error analysis."""
        try:
            import ollama
            from configs.config import MODEL_NAME, GPU_LAYERS

            prompt = f"""You are a code fixer. The following error occurred during build/test:

Error type: {analysis.get('error_type', 'unknown')}
Error message: {analysis.get('message', 'unknown')}
File: {analysis.get('file', 'unknown')}
Line: {analysis.get('line', 'unknown')}
Language: {language}

Full error output:
{analysis.get('raw_error', '')[:1500]}

Provide the corrected code. If it's a missing module, show the import. If it's a syntax error, show the fix. Be specific and provide the actual corrected code block."""

            options = {}
            if GPU_LAYERS is not None:
                options["num_gpu"] = GPU_LAYERS

            response = ollama.chat(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                options=options,
            )
            return response["message"]["content"]
        except Exception as e:
            write_log("BUILD_LOOP", f"LLM fix generation failed: {e}")
            return f"# Fix generation failed: {e}"

    def _apply_fix(self, fix: str, root: Path):
        """Apply a generated fix to the project.
        Currently logs the fix for manual review. In production, this would
        parse the LLM output and write the corrected files."""
        write_log("BUILD_LOOP", f"Generated fix (first 500 chars): {fix[:500]}")
        # Save fix to artifacts for review
        try:
            from automation.engine.artifacts import artifact_manager
            artifact_manager.save("build_fix", {"fix": fix[:5000], "timestamp": time.time()})
        except Exception:
            pass


build_test_fix_loop = BuildTestFixLoop()
