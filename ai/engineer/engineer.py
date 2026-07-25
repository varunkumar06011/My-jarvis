from pathlib import Path
from typing import Optional

from core.event_bus import bus
from ai.engineer.code_review import CodeReviewer
from ai.engineer.root_cause import RootCauseAnalyzer
from ai.engineer.bug_detection import BugDetector
from ai.engineer.generation import CodeGenerator


class AISoftwareEngineer:
    """Unified AI Software Engineer.
    Combines code review, root cause analysis, bug detection, and generation."""

    def __init__(self, root: str = "."):
        self.root = Path(root).resolve()
        self.reviewer = CodeReviewer(root)
        self.root_cause = RootCauseAnalyzer(root)
        self.bug_detector = BugDetector(root)
        self.generator = CodeGenerator(root)

    def review_code(self, filepath: str = None) -> dict:
        """Review a single file or the entire repository."""
        if filepath:
            return self.reviewer.review_file(filepath)
        return self.reviewer.review_repository()

    def analyze_failure(self, error: str = None, stack_trace: str = None,
                        file_path: str = None) -> dict:
        """Perform root cause analysis on a failure."""
        return self.root_cause.analyze(error=error, stack_trace=stack_trace, file_path=file_path)

    def detect_bugs(self) -> dict:
        """Run all bug detection checks."""
        return self.bug_detector.detect_all()

    def generate_tests(self, filepath: str, test_type: str = "unit") -> dict:
        """Generate unit or integration tests for a file."""
        if test_type == "unit":
            return self.generator.generate_unit_tests(filepath)
        elif test_type == "integration":
            return self.generator.generate_integration_tests(filepath)
        return {"error": f"Unknown test type: {test_type}"}

    def generate_docs(self, filepath: str) -> dict:
        """Generate documentation for a file."""
        return self.generator.generate_documentation(filepath)

    def generate_refactoring_plan(self, filepath: str) -> dict:
        """Generate a refactoring plan for a file."""
        return self.generator.generate_refactoring_plan(filepath)

    def generate_migration_plan(self, from_framework: str, to_framework: str) -> dict:
        """Generate a migration plan between frameworks."""
        return self.generator.generate_migration_plan(from_framework, to_framework)

    def full_analysis(self, filepath: str = None) -> dict:
        """Run a complete engineering analysis: review + bugs + tests + docs."""
        result = {}

        if filepath:
            result["review"] = self.review_code(filepath)
            result["refactoring_plan"] = self.generate_refactoring_plan(filepath)
            result["tests"] = self.generate_tests(filepath)
            result["docs"] = self.generate_docs(filepath)
        else:
            result["review"] = self.review_code()
            result["bugs"] = self.detect_bugs()

        bus.publish("EngineeringAnalysisCompleted", {
            "root": str(self.root),
            "sections": list(result.keys()),
        })

        return result


ai_engineer = AISoftwareEngineer()
