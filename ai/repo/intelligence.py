from pathlib import Path
from typing import Optional

from core.event_bus import bus
from ai.repo.discovery import RepositoryDiscovery
from ai.repo.languages import LanguageDetector
from ai.repo.static_analysis import StaticAnalyzer
from ai.repo.frameworks import FrameworkDetector
from ai.repo.knowledge import RepositoryKnowledge
from ai.repo.query_engine import RepositoryQueryEngine


class RepositoryIntelligence:
    """Unified entry point for the Repository Intelligence Platform.
    Orchestrates discovery, language detection, static analysis,
    framework detection, knowledge identification, and querying."""

    def __init__(self, root: str = "."):
        self.root = Path(root).resolve()
        self._discovery = RepositoryDiscovery(root)
        self._languages = LanguageDetector(root)
        self._analyzer = StaticAnalyzer(root)
        self._frameworks = FrameworkDetector(root)
        self._knowledge = RepositoryKnowledge(root)
        self._query_engine = RepositoryQueryEngine(root)
        self._indexed = False
        self._cache: Optional[dict] = None

    def analyze_all(self) -> dict:
        """Run full repository analysis and cache results."""
        discovery = self._discovery.discover()
        languages = self._languages.detect()
        frameworks = self._frameworks.detect()
        analysis = self._analyzer.analyze()
        knowledge = self._knowledge.identify()

        self._cache = {
            "discovery": discovery,
            "languages": languages,
            "frameworks": frameworks,
            "analysis": analysis,
            "knowledge": knowledge,
        }
        self._indexed = True

        bus.publish("RepositoryIntelligenceReady", {
            "root": str(self.root),
            "modules": analysis["summary"]["total_modules"],
            "symbols": analysis["summary"]["total_symbols"],
            "languages": languages.get("primary_language"),
            "framework": frameworks.get("primary_framework"),
        })

        return self._cache

    def query(self, question: str) -> dict:
        """Answer a natural language question about the repository."""
        if not self._indexed:
            self.analyze_all()
        return self._query_engine.query(question)

    def get_summary(self) -> dict:
        """Return a high-level summary of the repository."""
        if not self._indexed:
            self.analyze_all()

        return {
            "root": str(self.root),
            "vcs": self._cache["discovery"].get("vcs"),
            "primary_language": self._cache["languages"].get("primary_language"),
            "primary_framework": self._cache["frameworks"].get("primary_framework"),
            "is_monorepo": self._cache["discovery"].get("is_monorepo") is not None,
            "package_managers": self._cache["discovery"].get("package_managers", []),
            "build_systems": self._cache["discovery"].get("build_systems", []),
            "module_count": self._cache["analysis"]["summary"]["total_modules"],
            "symbol_count": self._cache["analysis"]["summary"]["total_symbols"],
            "api_count": self._cache["analysis"]["summary"]["api_endpoints"],
            "knowledge_summary": self._cache["knowledge"]["summary"],
        }

    def get_analysis(self) -> dict:
        if not self._indexed:
            self.analyze_all()
        return self._cache["analysis"]

    def get_knowledge(self) -> dict:
        if not self._indexed:
            self.analyze_all()
        return self._cache["knowledge"]

    def get_discovery(self) -> dict:
        if not self._indexed:
            self.analyze_all()
        return self._cache["discovery"]

    def get_frameworks(self) -> dict:
        if not self._indexed:
            self.analyze_all()
        return self._cache["frameworks"]

    def get_languages(self) -> dict:
        if not self._indexed:
            self.analyze_all()
        return self._cache["languages"]


repo_intelligence = RepositoryIntelligence()
