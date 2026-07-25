import re
from pathlib import Path
from typing import Optional

from ai.repo.static_analysis import StaticAnalyzer
from ai.repo.knowledge import RepositoryKnowledge
from ai.repo.frameworks import FrameworkDetector
from ai.repo.languages import LanguageDetector
from ai.repo.discovery import RepositoryDiscovery


class RepositoryQueryEngine:
    """Answers natural language questions about a repository using
    structural analysis, knowledge identification, and symbol search."""

    def __init__(self, root: str = "."):
        self.root = Path(root).resolve()
        self._analyzer = StaticAnalyzer(root)
        self._knowledge = RepositoryKnowledge(root)
        self._frameworks = FrameworkDetector(root)
        self._languages = LanguageDetector(root)
        self._discovery = RepositoryDiscovery(root)
        self._analysis: Optional[dict] = None
        self._knowledge_data: Optional[dict] = None
        self._framework_data: Optional[dict] = None
        self._language_data: Optional[dict] = None
        self._discovery_data: Optional[dict] = None

    def index(self) -> dict:
        """Pre-compute all analysis data for fast querying."""
        self._discovery_data = self._discovery.discover()
        self._language_data = self._languages.detect()
        self._framework_data = self._frameworks.detect()
        self._analysis = self._analyzer.analyze()
        self._knowledge_data = self._knowledge.identify()

        return {
            "discovery": self._discovery_data,
            "languages": self._language_data,
            "frameworks": self._framework_data,
            "analysis": self._analysis["summary"],
            "knowledge": self._knowledge_data["summary"],
        }

    def query(self, question: str) -> dict:
        """Answer a natural language question about the repository."""
        if self._analysis is None:
            self.index()

        q_lower = question.lower().strip()

        if not q_lower.endswith("?"):
            q_lower += "?"

        intent = self._classify_intent(q_lower)

        if intent == "auth":
            return self._find_authentication()
        elif intent == "api_create":
            return self._find_api_for_action(q_lower, "create", "invoice")
        elif intent == "service":
            return self._find_service(q_lower)
        elif intent == "module_owner":
            return self._find_module_owner(q_lower)
        elif intent == "where_is":
            return self._find_implementation(q_lower)
        elif intent == "which_api":
            return self._find_apis()
        elif intent == "structure":
            return self._describe_structure()
        elif intent == "frameworks":
            return {"frameworks": self._framework_data}
        elif intent == "languages":
            return {"languages": self._language_data}
        else:
            return self._general_search(q_lower)

    def _classify_intent(self, question: str) -> str:
        if "auth" in question or "login" in question or "authentication" in question:
            return "auth"
        if "which api" in question and ("create" in question or "invoice" in question):
            return "api_create"
        if "which service" in question or "service" in question and ("print" in question or "kot" in question):
            return "service"
        if "which module" in question or "owns" in question or "responsible" in question:
            return "module_owner"
        if "where is" in question or "where are" in question or "implemented" in question:
            return "where_is"
        if "which api" in question or "what api" in question or "apis" in question:
            return "which_api"
        if "structure" in question or "architecture" in question or "layout" in question:
            return "structure"
        if "framework" in question:
            return "frameworks"
        if "language" in question or "languages" in question or "tech stack" in question:
            return "languages"
        return "general"

    def _find_authentication(self) -> dict:
        results = []
        auth_keywords = ["auth", "login", "jwt", "token", "password", "oauth", "session", "credential", "passport", "spring security"]

        for kw in auth_keywords:
            for symbol_name, info in self._analysis["symbol_index"].items():
                if kw in symbol_name.lower() or kw in info.get("file", "").lower():
                    results.append({
                        "symbol": symbol_name,
                        "file": info["file"],
                        "line": info.get("line", 0),
                        "type": info["type"],
                    })

            for item in self._knowledge_data.get("middleware", []):
                if kw in item.get("file", "").lower() or kw in item.get("match", "").lower():
                    results.append({"file": item["file"], "type": "middleware"})

            for item in self._knowledge_data.get("config", []):
                if kw in item.get("file", "").lower():
                    results.append({"file": item["file"], "type": "config"})

        seen = set()
        unique = []
        for r in results:
            key = f"{r.get('file', '')}:{r.get('line', r.get('type', ''))}"
            if key not in seen:
                seen.add(key)
                unique.append(r)

        return {
            "question": "Where is authentication implemented?",
            "answer": f"Found {len(unique)} authentication-related locations",
            "locations": unique[:20],
        }

    def _find_api_for_action(self, question: str, action: str, entity: str) -> dict:
        results = []

        for endpoint in self._analysis["api_graph"]:
            decorator = endpoint.get("decorator", "").lower()
            func_name = endpoint.get("function", "").lower()

            if action in decorator or action in func_name or entity in decorator or entity in func_name:
                results.append(endpoint)

        if not results:
            for endpoint in self._analysis["api_graph"]:
                results.append(endpoint)

        return {
            "question": f"Which API {action}s {entity}s?",
            "answer": f"Found {len(results)} matching API endpoints",
            "endpoints": results[:20],
        }

    def _find_service(self, question: str) -> dict:
        keywords = self._extract_keywords(question, exclude=["which", "service", "the", "a", "an", "is", "what"])

        results = []
        for symbol_name, info in self._analysis["symbol_index"].items():
            if info["type"] != "class":
                continue
            name_lower = symbol_name.lower()
            if any(kw in name_lower for kw in keywords) or "service" in name_lower or "manager" in name_lower:
                results.append({
                    "symbol": symbol_name,
                    "file": info["file"],
                    "line": info.get("line", 0),
                })

        return {
            "question": question,
            "answer": f"Found {len(results)} service-like components",
            "services": results[:20],
        }

    def _find_module_owner(self, question: str) -> dict:
        keywords = self._extract_keywords(question, exclude=["which", "module", "owns", "responsible", "for", "the", "a", "an", "routing", "what"])

        results = []
        for module_name, info in self._analysis["module_graph"].items():
            module_lower = module_name.lower()
            if any(kw in module_lower for kw in keywords):
                results.append({
                    "module": module_name,
                    "file": info["path"],
                    "classes": info.get("classes", []),
                    "functions": info.get("functions", []),
                })

            for func in info.get("functions", []):
                if any(kw in func.lower() for kw in keywords):
                    results.append({
                        "module": module_name,
                        "file": info["path"],
                        "function": func,
                    })

        return {
            "question": question,
            "answer": f"Found {len(results)} owning modules",
            "modules": results[:20],
        }

    def _find_implementation(self, question: str) -> dict:
        keywords = self._extract_keywords(question, exclude=["where", "is", "are", "the", "a", "an", "implemented", "defined", "located", "found"])

        results = []
        for symbol_name, info in self._analysis["symbol_index"].items():
            if any(kw in symbol_name.lower() for kw in keywords):
                results.append({
                    "symbol": symbol_name,
                    "file": info["file"],
                    "line": info.get("line", 0),
                    "type": info["type"],
                })

        for item in self._knowledge_data.get("controllers", []) + self._knowledge_data.get("services", []):
            if any(kw in item.get("file", "").lower() for kw in keywords):
                results.append({"file": item["file"], "type": "knowledge_match"})

        seen = set()
        unique = []
        for r in results:
            key = f"{r.get('file', '')}:{r.get('line', r.get('type', ''))}"
            if key not in seen:
                seen.add(key)
                unique.append(r)

        return {
            "question": question,
            "answer": f"Found {len(unique)} implementation locations",
            "locations": unique[:20],
        }

    def _find_apis(self) -> dict:
        return {
            "question": "Which APIs exist?",
            "answer": f"Found {len(self._analysis['api_graph'])} API endpoints",
            "endpoints": self._analysis["api_graph"][:50],
        }

    def _describe_structure(self) -> dict:
        return {
            "question": "What is the repository structure?",
            "answer": "Repository structure analysis",
            "discovery": self._discovery_data,
            "primary_language": self._language_data.get("primary_language"),
            "primary_framework": self._framework_data.get("primary_framework"),
            "summary": self._analysis["summary"],
            "knowledge_summary": self._knowledge_data["summary"],
        }

    def _general_search(self, question: str) -> dict:
        keywords = self._extract_keywords(question)

        results = []
        for symbol_name, info in self._analysis["symbol_index"].items():
            if any(kw in symbol_name.lower() for kw in keywords):
                results.append({
                    "symbol": symbol_name,
                    "file": info["file"],
                    "line": info.get("line", 0),
                    "type": info["type"],
                })

        for module_name, info in self._analysis["module_graph"].items():
            if any(kw in module_name.lower() for kw in keywords):
                results.append({
                    "module": module_name,
                    "file": info["path"],
                })

        return {
            "question": question,
            "answer": f"Found {len(results)} matches",
            "matches": results[:20],
        }

    def _extract_keywords(self, question: str, exclude: list = None) -> list:
        if exclude is None:
            exclude = {"which", "what", "where", "the", "a", "an", "is", "are", "how", "why", "when", "who"}

        words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', question)
        keywords = [w.lower() for w in words if w.lower() not in exclude and len(w) > 2]
        return keywords


repo_query_engine = RepositoryQueryEngine()
