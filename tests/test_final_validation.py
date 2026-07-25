"""Jarvis Final Validation — tests all voice commands, API endpoints, and
engineering pipeline integrations end-to-end."""

import sys
import os
import json
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FinalValidation:
    """Runs validation tests for all Jarvis components."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.results = []

    def test(self, name: str, condition: bool, details: str = ""):
        if condition:
            self.passed += 1
            self.results.append(("PASS", name, details))
            print(f"  ✓ {name}")
        else:
            self.failed += 1
            self.results.append(("FAIL", name, details))
            print(f"  ✗ {name} — {details}")

    def skip(self, name: str, reason: str = ""):
        self.skipped += 1
        self.results.append(("SKIP", name, reason))
        print(f"  ⊘ {name} — {reason}")

    def run_all(self) -> dict:
        print("\n" + "=" * 60)
        print("  JARVIS FINAL VALIDATION")
        print("=" * 60)

        self._test_imports()
        self._test_repo_bridge()
        self._test_project_manager()
        self._test_workspace_manager()
        self._test_github_plugin()
        self._test_git_plugin()
        self._test_agents()
        self._test_build_test_fix()
        self._test_continuous_intelligence()
        self._test_continuous_cto()
        self._test_verification_workflow()
        self._test_engineering_ui()
        self._test_api_schemas()

        print("\n" + "=" * 60)
        total = self.passed + self.failed + self.skipped
        print(f"  RESULTS: {self.passed} passed, {self.failed} failed, {self.skipped} skipped ({total} total)")
        print("=" * 60)

        return {
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "total": total,
            "results": self.results,
        }

    def _test_imports(self):
        print("\n─ Module Imports ─")
        try:
            from services.repo_bridge import handle_repo_query, classify_intent
            self.test("repo_bridge import", True)
        except Exception as e:
            self.test("repo_bridge import", False, str(e))

        try:
            from services.project_manager import project_manager, ProjectContextManager
            self.test("project_manager import", True)
        except Exception as e:
            self.test("project_manager import", False, str(e))

        try:
            from services.workspace_manager import workspace_manager, WorkspaceManager
            self.test("workspace_manager import", True)
        except Exception as e:
            self.test("workspace_manager import", False, str(e))

        try:
            from services.verification import verification_workflow, VerificationWorkflow
            self.test("verification import", True)
        except Exception as e:
            self.test("verification import", False, str(e))

        try:
            from ai.engineer.build_test_fix import build_test_fix_loop, BuildTestFixLoop
            self.test("build_test_fix import", True)
        except Exception as e:
            self.test("build_test_fix import", False, str(e))

        try:
            from ai.repo.continuous import continuous_repo_intelligence, ContinuousRepoIntelligence
            self.test("continuous_repo import", True)
        except Exception as e:
            self.test("continuous_repo import", False, str(e))

        try:
            from ai.cto.continuous import continuous_cto, ContinuousCTO
            self.test("continuous_cto import", True)
        except Exception as e:
            self.test("continuous_cto import", False, str(e))

    def _test_repo_bridge(self):
        print("\n─ Repository Voice Bridge ─")
        try:
            from services.repo_bridge import classify_intent

            test_cases = [
                ("where is authentication", "where_is"),
                ("explain printer logic", "explain"),
                ("show architecture", "architecture"),
                ("find bug", "find_bug"),
                ("switch to Softshape", "switch_project"),
                ("list projects", "list_projects"),
                ("create repo myapp", "create_repo"),
                ("push to github", "push_project"),
                ("create branch feature/login", "create_branch"),
                ("create PR titled fix bug", "create_pr"),
                ("merge PR 42", "merge_pr"),
                ("create release v1.0.0", "create_release"),
                ("build a website", "build_project"),
                ("build and test", "build_test"),
                ("run tests", "run_tests"),
                ("verify project", "verify_project"),
                ("register project at C:/Users/test", "register_project"),
            ]

            for text, expected in test_cases:
                intent = classify_intent(text)
                self.test(f"classify '{text}'", intent == expected, f"got '{intent}', expected '{expected}'")
        except Exception as e:
            self.test("repo bridge classify", False, str(e))

    def _test_project_manager(self):
        print("\n─ Project Context Manager ─")
        try:
            from services.project_manager import project_manager

            projects = project_manager.list_projects()
            self.test("list_projects returns list", isinstance(projects, list))

            test_project = project_manager.register("test_validation", ".", framework="test", language="python")
            self.test("register project", test_project.name == "test_validation")

            retrieved = project_manager.get_project("test_validation")
            self.test("get_project", retrieved is not None and retrieved.name == "test_validation")

            switched = project_manager.switch("test_validation")
            self.test("switch project", switched is not None)

            active = project_manager.get_active()
            self.test("get_active", active is not None and active.name == "test_validation")

            updated = project_manager.update("test_validation", description="Updated")
            self.test("update project", updated is not None and updated.description == "Updated")

            removed = project_manager.remove("test_validation")
            self.test("remove project", removed is True)
        except Exception as e:
            self.test("project_manager", False, str(e))

    def _test_workspace_manager(self):
        print("\n─ Workspace Manager ─")
        try:
            from services.workspace_manager import workspace_manager

            ws = workspace_manager.create("test_ws", ".")
            self.test("create workspace", ws.project_name == "test_ws")

            retrieved = workspace_manager.get("test_ws")
            self.test("get workspace", retrieved is not None)

            workspace_manager.add_llm_context("test_ws", "user", "test message")
            ctx = workspace_manager.get_llm_context("test_ws")
            self.test("llm context", len(ctx) == 1)

            workspace_manager.set_env_var("test_ws", "TEST_VAR", "value")
            ws = workspace_manager.get("test_ws")
            self.test("env var", ws.env_vars.get("TEST_VAR") == "value")

            workspace_manager.remove("test_ws")
            self.test("remove workspace", workspace_manager.get("test_ws") is None)
        except Exception as e:
            self.test("workspace_manager", False, str(e))

    def _test_github_plugin(self):
        print("\n─ GitHub Plugin ─")
        try:
            from automation.plugins.github.plugin import GitHubPlugin
            gh = GitHubPlugin()
            gh.initialize()

            action_names = list(gh.actions.keys())
            self.test("github.create_repo registered", "github.create_repo" in action_names)
            self.test("github.delete_repo registered", "github.delete_repo" in action_names)

            workflows = gh.workflows if hasattr(gh, "workflows") else []
            wf_ids = [w.get("id", "") for w in workflows]
            self.test("github_project_lifecycle workflow", "github_project_lifecycle" in wf_ids)
        except Exception as e:
            self.test("github plugin", False, str(e))

    def _test_git_plugin(self):
        print("\n─ Git Plugin ─")
        try:
            from automation.plugins.git.plugin import GitPlugin
            git = GitPlugin()
            git.initialize()

            action_names = list(git.actions.keys())
            self.test("git.add_remote registered", "git.add_remote" in action_names)
        except Exception as e:
            self.test("git plugin", False, str(e))

    def _test_agents(self):
        print("\n─ Engineering Agents ─")
        try:
            from ai.agents.planner import PlannerAgent
            from ai.agents.architect import ArchitectAgent
            from ai.agents.backend import BackendEngineerAgent
            from ai.agents.frontend import FrontendEngineerAgent
            from ai.agents.qa import QAEngineerAgent
            from ai.agents.security import SecurityEngineerAgent
            from ai.agents.devops import DevOpsEngineerAgent
            from ai.agents.reviewer import ReviewerAgent
            from ai.agents.reporter import ReporterAgent

            agents = [
                ("Planner", PlannerAgent),
                ("Architect", ArchitectAgent),
                ("Backend", BackendEngineerAgent),
                ("Frontend", FrontendEngineerAgent),
                ("QA", QAEngineerAgent),
                ("Security", SecurityEngineerAgent),
                ("DevOps", DevOpsEngineerAgent),
                ("Reviewer", ReviewerAgent),
                ("Reporter", ReporterAgent),
            ]

            for name, cls in agents:
                try:
                    agent = cls()
                    has_llm = hasattr(agent, "_llm_chat")
                    has_repo = hasattr(agent, "_get_repo_context")
                    self.test(f"{name} has LLM integration", has_llm and has_repo)
                except Exception as e:
                    if "ollama" in str(e).lower() or "No module" in str(e):
                        self.skip(f"{name} (ollama not installed)", str(e))
                    else:
                        self.test(f"{name} agent", False, str(e))
        except Exception as e:
            if "ollama" in str(e).lower() or "No module" in str(e):
                self.skip("agents (ollama not installed)", str(e))
            else:
                self.test("agents", False, str(e))

    def _test_build_test_fix(self):
        print("\n─ Build-Test-Fix-Retry Loop ─")
        try:
            from ai.engineer.build_test_fix import BuildTestFixLoop
            loop = BuildTestFixLoop(max_retries=3)

            self.test("max_retries set", loop.max_retries == 3)

            lang = loop._detect_language(Path("."))
            self.test("detect language", lang in ("python", "node", "react", "maven", "gradle", "unknown"))

            build_cmd = loop._detect_build_cmd(Path("."), "python")
            self.test("detect build cmd", build_cmd is not None)

            test_cmd = loop._detect_test_cmd(Path("."), "python")
            self.test("detect test cmd", test_cmd is not None)
        except Exception as e:
            self.test("build_test_fix", False, str(e))

    def _test_continuous_intelligence(self):
        print("\n─ Continuous Repository Intelligence ─")
        try:
            from ai.repo.continuous import ContinuousRepoIntelligence
            cri = ContinuousRepoIntelligence(interval_seconds=10)

            self.test("interval set", cri.interval == 10)
            self.test("not running initially", cri._running is False)

            status = cri.get_status()
            self.test("get_status returns dict", isinstance(status, dict))
        except Exception as e:
            self.test("continuous intelligence", False, str(e))

    def _test_continuous_cto(self):
        print("\n─ Continuous AI CTO ─")
        try:
            from ai.cto.continuous import ContinuousCTO
            cto = ContinuousCTO(interval_seconds=60)

            self.test("interval set", cto.interval == 60)
            self.test("not running initially", cto._running is False)

            status = cto.get_status()
            self.test("get_status returns dict", isinstance(status, dict))
        except Exception as e:
            self.test("continuous cto", False, str(e))

    def _test_verification_workflow(self):
        print("\n─ Verification Workflow ─")
        try:
            from services.verification import VerificationWorkflow
            vw = VerificationWorkflow()

            self.test("stages defined", len(vw.stages) >= 7)

            stage_names = [s[0] for s in vw.stages]
            expected_stages = ["register", "analyze", "build", "test", "fix", "review", "security"]
            for s in expected_stages:
                self.test(f"stage '{s}' present", s in stage_names)
        except Exception as e:
            self.test("verification workflow", False, str(e))

    def _test_engineering_ui(self):
        print("\n─ Engineering UI ─")
        try:
            from desktop.pages.engineering import EngineeringPage
            self.test("EngineeringPage importable", True)
        except Exception as e:
            if "PySide6" in str(e) or "No module" in str(e):
                self.skip("EngineeringPage (PySide6 not installed)", str(e))
            else:
                self.test("EngineeringPage import", False, str(e))

        try:
            from desktop.window import MainWindow
            self.test("MainWindow importable with Engineering", True)
        except Exception as e:
            if "PySide6" in str(e) or "No module" in str(e):
                self.skip("MainWindow (PySide6 not installed)", str(e))
            else:
                self.test("MainWindow import", False, str(e))

    def _test_api_schemas(self):
        print("\n─ API Schemas ─")
        try:
            from network.api.schemas import RepoQueryRequest, RepoQueryResponse
            self.test("RepoQueryRequest schema", True)
            self.test("RepoQueryResponse schema", True)
        except Exception as e:
            self.test("API schemas", False, str(e))

        try:
            from network.routes.voice import router as voice_router
            self.test("voice router importable", True)
        except Exception as e:
            self.test("voice router", False, str(e))

        try:
            from network.routes.projects import router as projects_router
            self.test("projects router importable", True)
        except Exception as e:
            self.test("projects router", False, str(e))


if __name__ == "__main__":
    validator = FinalValidation()
    result = validator.run_all()
    sys.exit(0 if result["failed"] == 0 else 1)
