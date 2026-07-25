"""Tests for the AI Engineering Ecosystem (Steps 30-34)."""
import os
import sys
import unittest
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestStep30RepositoryIntelligence(unittest.TestCase):
    """Step 30: Repository Intelligence Platform."""

    def setUp(self):
        self.root = str(PROJECT_ROOT)

    def test_discovery(self):
        from ai.repo.discovery import RepositoryDiscovery
        result = RepositoryDiscovery(self.root).discover()
        self.assertIn("root", result)
        self.assertIn("vcs", result)
        self.assertIn("package_managers", result)

    def test_language_detection(self):
        from ai.repo.languages import LanguageDetector
        result = LanguageDetector(self.root).detect()
        self.assertIn("languages", result)
        self.assertIn("primary_language", result)
        self.assertGreater(result["total_files"], 0)

    def test_static_analysis(self):
        from ai.repo.static_analysis import StaticAnalyzer
        result = StaticAnalyzer(self.root).analyze()
        self.assertIn("summary", result)
        self.assertIn("symbol_index", result)
        self.assertIn("module_graph", result)
        self.assertGreater(result["summary"]["total_modules"], 0)

    def test_framework_detection(self):
        from ai.repo.frameworks import FrameworkDetector
        result = FrameworkDetector(self.root).detect()
        self.assertIn("frameworks", result)

    def test_repository_knowledge(self):
        from ai.repo.knowledge import RepositoryKnowledge
        result = RepositoryKnowledge(self.root).identify()
        self.assertIn("controllers", result)
        self.assertIn("services", result)
        self.assertIn("models", result)
        self.assertIn("tests", result)
        self.assertIn("summary", result)

    def test_query_engine(self):
        from ai.repo.query_engine import RepositoryQueryEngine
        qe = RepositoryQueryEngine(self.root)
        qe.index()
        result = qe.query("Where is authentication implemented?")
        self.assertIn("answer", result)

    def test_intelligence_orchestrator(self):
        from ai.repo.intelligence import RepositoryIntelligence
        ri = RepositoryIntelligence(self.root)
        summary = ri.get_summary()
        self.assertIn("root", summary)


class TestStep31KnowledgeEngine(unittest.TestCase):
    """Step 31: Enterprise Knowledge Engine (RAG)."""

    def setUp(self):
        self.root = str(PROJECT_ROOT)

    def test_indexer(self):
        from ai.knowledge.indexer import KnowledgeIndexer
        indexer = KnowledgeIndexer()
        result = indexer.index_repository(self.root, "jarvis-test")
        self.assertIn("indexed_files", result)
        self.assertGreater(result["indexed_files"], 0)
        indexer.clear("jarvis-test")

    def test_semantic_search(self):
        from ai.knowledge.indexer import KnowledgeIndexer
        from ai.knowledge.search import SemanticSearch
        indexer = KnowledgeIndexer()
        indexer.index_repository(self.root, "jarvis-test")
        search = SemanticSearch()
        search.build_index()
        results = search.semantic_search("event bus", limit=5, repo="jarvis-test")
        self.assertIsInstance(results, list)
        indexer.clear("jarvis-test")

    def test_hybrid_search(self):
        from ai.knowledge.indexer import KnowledgeIndexer
        from ai.knowledge.search import SemanticSearch
        indexer = KnowledgeIndexer()
        indexer.index_repository(self.root, "jarvis-test")
        search = SemanticSearch()
        search.build_index()
        results = search.hybrid_search("service registry", limit=5, repo="jarvis-test")
        self.assertIsInstance(results, list)
        indexer.clear("jarvis-test")

    def test_context_builder(self):
        from ai.knowledge.indexer import KnowledgeIndexer
        from ai.knowledge.context_builder import ContextBuilder
        indexer = KnowledgeIndexer()
        indexer.index_repository(self.root, "jarvis-test")
        cb = ContextBuilder()
        result = cb.build_context("event bus publish subscribe", repo="jarvis-test")
        self.assertIn("context", result)
        self.assertIn("sources", result)
        indexer.clear("jarvis-test")

    def test_incremental_indexer(self):
        from ai.knowledge.incremental import IncrementalIndexer
        inc = IncrementalIndexer()
        result = inc.register_repo(self.root, "jarvis-test")
        self.assertIn("repo", result)
        changes = inc.detect_changes("jarvis-test")
        self.assertIn("added", changes)
        self.assertIn("modified", changes)
        self.assertIn("removed", changes)

    def test_multi_repo_search(self):
        from ai.knowledge.indexer import KnowledgeIndexer
        from ai.knowledge.multi_repo import MultiRepositorySearch
        indexer = KnowledgeIndexer()
        indexer.index_repository(self.root, "jarvis-test")
        mr = MultiRepositorySearch()
        results = mr.search("event bus", limit=5)
        self.assertIsInstance(results, list)
        indexer.clear("jarvis-test")

    def test_knowledge_memory(self):
        from ai.knowledge.knowledge_memory import KnowledgeMemory
        km = KnowledgeMemory()
        entry = km.store("decision", "Test Decision", "Test content for testing", tags=["test"])
        self.assertEqual(entry["title"], "Test Decision")
        results = km.search("Test Decision")
        self.assertGreater(len(results), 0)
        km.delete(entry["id"])

    def test_knowledge_engine(self):
        from ai.knowledge.engine import KnowledgeEngine
        engine = KnowledgeEngine()
        stats = engine.stats()
        self.assertIn("index", stats)
        self.assertIn("memory", stats)


class TestStep32AISoftwareEngineer(unittest.TestCase):
    """Step 32: AI Software Engineer."""

    def setUp(self):
        self.root = str(PROJECT_ROOT)

    def test_code_review(self):
        from ai.engineer.code_review import CodeReviewer
        reviewer = CodeReviewer(self.root)
        result = reviewer.review_file("core/event_bus.py")
        self.assertIn("issues", result)
        self.assertIn("quality_score", result)

    def test_repository_review(self):
        from ai.engineer.code_review import CodeReviewer
        reviewer = CodeReviewer(self.root)
        result = reviewer.review_repository()
        self.assertIn("summary", result)
        self.assertIn("files", result)

    def test_root_cause_analysis(self):
        from ai.engineer.root_cause import RootCauseAnalyzer
        rca = RootCauseAnalyzer(self.root)
        result = rca.analyze(error="ImportError: No module named 'foo'", stack_trace='File "test.py", line 10, in main\nImportError: No module named \'foo\'')
        self.assertIn("findings", result)
        self.assertIn("root_causes", result)

    def test_bug_detection(self):
        from ai.engineer.bug_detection import BugDetector
        detector = BugDetector(self.root)
        result = detector.detect_dead_code()
        self.assertIsInstance(result, list)

    def test_bug_detection_circular(self):
        from ai.engineer.bug_detection import BugDetector
        detector = BugDetector(self.root)
        result = detector.detect_circular_dependencies()
        self.assertIsInstance(result, list)

    def test_unit_test_generation(self):
        from ai.engineer.generation import CodeGenerator
        gen = CodeGenerator(self.root)
        result = gen.generate_unit_tests("core/event_bus.py")
        self.assertIn("test_code", result)
        self.assertIn("test_file", result)

    def test_documentation_generation(self):
        from ai.engineer.generation import CodeGenerator
        gen = CodeGenerator(self.root)
        result = gen.generate_documentation("core/event_bus.py")
        self.assertIn("documentation", result)

    def test_refactoring_plan(self):
        from ai.engineer.generation import CodeGenerator
        gen = CodeGenerator(self.root)
        result = gen.generate_refactoring_plan("core/event_bus.py")
        self.assertIn("refactoring_plan", result)

    def test_migration_plan(self):
        from ai.engineer.generation import CodeGenerator
        gen = CodeGenerator(self.root)
        result = gen.generate_migration_plan("Django", "FastAPI")
        self.assertIn("phases", result)
        self.assertEqual(len(result["phases"]), 5)

    def test_engineer_orchestrator(self):
        from ai.engineer.engineer import AISoftwareEngineer
        eng = AISoftwareEngineer(self.root)
        result = eng.review_code("core/event_bus.py")
        self.assertIn("issues", result)


class TestStep33EngineeringAgents(unittest.TestCase):
    """Step 33: AI Engineering Agents."""

    def test_agent_initialization(self):
        from ai.agents.coordinator import agent_coordinator
        agents = agent_coordinator.list_agents()
        self.assertEqual(len(agents), 9)

    def test_agent_names(self):
        from ai.agents.coordinator import agent_coordinator
        names = [a["name"] for a in agent_coordinator.list_agents()]
        expected = ["Planner", "Architect", "BackendEngineer", "FrontendEngineer",
                    "QAEngineer", "SecurityEngineer", "DevOpsEngineer", "Reviewer", "Reporter"]
        self.assertEqual(names, expected)

    def test_agent_has_prompt(self):
        from ai.agents.coordinator import agent_coordinator
        for name, agent in agent_coordinator.agents.items():
            self.assertTrue(len(agent.system_prompt) > 0, f"Agent {name} has empty prompt")

    def test_agent_has_tools(self):
        from ai.agents.coordinator import agent_coordinator
        for name, agent in agent_coordinator.agents.items():
            self.assertTrue(len(agent.tools) > 0, f"Agent {name} has no tools")

    def test_agent_has_permissions(self):
        from ai.agents.coordinator import agent_coordinator
        for name, agent in agent_coordinator.agents.items():
            self.assertIsNotNone(agent.permissions, f"Agent {name} has no permissions")

    def test_agent_has_memory(self):
        from ai.agents.coordinator import agent_coordinator
        for name, agent in agent_coordinator.agents.items():
            self.assertEqual(agent.memory.agent_name, name)

    def test_agent_has_metrics(self):
        from ai.agents.coordinator import agent_coordinator
        for name, agent in agent_coordinator.agents.items():
            self.assertEqual(agent.metrics.agent_name, name)

    def test_single_agent_execution(self):
        from ai.agents.coordinator import agent_coordinator
        result = agent_coordinator.run_single_agent("Planner", {"type": "plan", "requirements": "Build a REST API"})
        self.assertEqual(result["status"], "ok")

    def test_pipeline_execution(self):
        from ai.agents.coordinator import agent_coordinator
        result = agent_coordinator.run_pipeline({"type": "build", "requirements": "Build a web app"})
        self.assertIn(result["status"], ("completed", "failed"))
        self.assertIn("session_id", result)

    def test_pipeline_status(self):
        from ai.agents.coordinator import agent_coordinator
        status = agent_coordinator.pipeline_status()
        self.assertEqual(status["agent_count"], 9)
        self.assertIn("pipeline_order", status)

    def test_agent_status(self):
        from ai.agents.coordinator import agent_coordinator
        status = agent_coordinator.get_agent_status("Planner")
        self.assertEqual(status["name"], "Planner")
        self.assertIn("status", status)


class TestStep34DevelopmentEcosystem(unittest.TestCase):
    """Step 34: Development Ecosystem."""

    def setUp(self):
        self.root = str(PROJECT_ROOT)

    def test_source_control_git_status(self):
        from ai.ecosystem.source_control import source_control
        result = source_control.git_status(self.root)
        self.assertIn("status", result)

    def test_source_control_git_log(self):
        from ai.ecosystem.source_control import source_control
        result = source_control.git_log(self.root, count=5)
        self.assertIn("status", result)

    def test_source_control_git_branch(self):
        from ai.ecosystem.source_control import source_control
        result = source_control.git_branch(self.root)
        self.assertIn("status", result)

    def test_source_control_branch_health(self):
        from ai.ecosystem.source_control import source_control
        result = source_control.git_branch_health(self.root)
        self.assertIn("status", result)

    def test_ide_detection(self):
        from ai.ecosystem.ide import IDEIntegration
        ides = IDEIntegration(self.root).detect_ides()
        self.assertIsInstance(ides, list)

    def test_container_docker_status(self):
        from ai.ecosystem.containers import container_integration
        result = container_integration.docker_status()
        self.assertIn("status", result)

    def test_container_analyze_dockerfile(self):
        from ai.ecosystem.containers import container_integration
        dockerfile = PROJECT_ROOT / "Dockerfile"
        if dockerfile.exists():
            result = container_integration.analyze_dockerfile("Dockerfile")
            self.assertIn("status", result)

    def test_build_system_detection(self):
        from ai.ecosystem.build import BuildSystemIntegration
        systems = BuildSystemIntegration(self.root).detect_build_systems()
        self.assertIsInstance(systems, list)

    def test_cicd_detection(self):
        from ai.ecosystem.cicd import CICDIntegration
        detected = CICDIntegration(self.root).detect_cicd()
        self.assertIsInstance(detected, list)

    def test_ecosystem_status(self):
        from ai.ecosystem.ecosystem import DevelopmentEcosystem
        status = DevelopmentEcosystem(self.root).ecosystem_status()
        self.assertIn("source_control", status)
        self.assertIn("ides", status)
        self.assertIn("build_systems", status)
        self.assertIn("cicd", status)


class TestFeatureFlags(unittest.TestCase):
    """Test that feature flags for the ecosystem are properly defined."""

    def test_flags_exist(self):
        from flags import flag_manager
        self.assertTrue(flag_manager.is_enabled("repo_intelligence"))
        self.assertTrue(flag_manager.is_enabled("knowledge_engine"))
        self.assertTrue(flag_manager.is_enabled("ai_engineer"))
        self.assertTrue(flag_manager.is_enabled("engineering_agents"))
        self.assertTrue(flag_manager.is_enabled("dev_ecosystem"))


if __name__ == "__main__":
    unittest.main()
