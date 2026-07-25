from pathlib import Path
from typing import Optional

from core.event_bus import bus
from ai.knowledge.indexer import knowledge_indexer
from ai.knowledge.search import semantic_search
from ai.knowledge.incremental import incremental_indexer
from ai.knowledge.multi_repo import multi_repo_search
from ai.knowledge.context_builder import context_builder
from ai.knowledge.knowledge_memory import knowledge_memory


class KnowledgeEngine:
    """Unified Enterprise Knowledge Engine (RAG).
    Orchestrates indexing, search, incremental updates, multi-repo search,
    context building, and knowledge memory persistence."""

    def __init__(self):
        self.indexer = knowledge_indexer
        self.search_engine = semantic_search
        self.incremental = incremental_indexer
        self.multi_repo = multi_repo_search
        self.context = context_builder
        self.memory = knowledge_memory

    def index_repository(self, root: str, repo_name: str = None) -> dict:
        """Index a repository for knowledge search."""
        result = self.indexer.index_repository(root, repo_name)
        self.search_engine.build_index()
        self.incremental.register_repo(root, repo_name)
        bus.publish("KnowledgeEngineIndexed", result)
        return result

    def search(self, query: str, limit: int = 20, repo: str = None) -> list:
        """Hybrid semantic + keyword search across indexed knowledge."""
        return self.search_engine.hybrid_search(query, limit=limit, repo=repo)

    def semantic_search(self, query: str, limit: int = 20, repo: str = None) -> list:
        """Pure semantic search."""
        return self.search_engine.semantic_search(query, limit=limit, repo=repo)

    def build_context(self, query: str, repo: str = None, max_chunks: int = 10) -> dict:
        """Build LLM-ready context for a query."""
        return self.context.build_context(query, repo=repo, max_chunks=max_chunks)

    def build_context_with_history(self, query: str, conversation_history: list = None,
                                    repo: str = None, max_chunks: int = 8) -> dict:
        """Build context with conversation history."""
        return self.context.build_context_with_history(
            query, conversation_history=conversation_history, repo=repo, max_chunks=max_chunks
        )

    def update_incremental(self, repo: str = None) -> dict:
        """Run incremental indexing update."""
        return self.incremental.update_incremental(repo)

    def detect_changes(self, repo: str = None) -> dict:
        """Detect file changes since last index."""
        return self.incremental.detect_changes(repo)

    def multi_repo_search(self, query: str, repos: list = None, limit: int = 20) -> list:
        """Search across multiple repositories."""
        return self.multi_repo.search(query, limit=limit, repos=repos)

    def remember(self, entry_type: str, title: str, content: str,
                 metadata: dict = None, tags: list = None, repo: str = None) -> dict:
        """Store a knowledge memory entry."""
        return self.memory.store(entry_type, title, content, metadata=metadata, tags=tags, repo=repo)

    def recall(self, query: str = None, entry_type: str = None,
               tags: list = None, repo: str = None, limit: int = 20) -> list:
        """Recall knowledge memory entries."""
        return self.memory.search(query=query, entry_type=entry_type, tags=tags, repo=repo, limit=limit)

    def stats(self) -> dict:
        """Get overall knowledge engine statistics."""
        return {
            "index": self.indexer.stats(),
            "memory": self.memory.stats(),
            "watched_repos": self.incremental.list_watched_repos(),
            "change_log": self.incremental.get_change_log(limit=5),
        }


knowledge_engine = KnowledgeEngine()
