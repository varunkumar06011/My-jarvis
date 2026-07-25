from typing import Optional

from ai.knowledge.indexer import knowledge_indexer
from ai.knowledge.search import semantic_search


class MultiRepositorySearch:
    """Search across multiple indexed repositories simultaneously."""

    def search(self, query: str, limit: int = 20, repos: list = None) -> list:
        """Search across all or specified repositories."""
        results = semantic_search.hybrid_search(query, limit=limit * 3)

        if repos:
            results = [r for r in results if r.get("repo") in repos]

        return results[:limit]

    def search_by_language(self, query: str, language: str, limit: int = 20) -> list:
        """Search within a specific programming language across all repos."""
        results = semantic_search.hybrid_search(query, limit=limit * 3)
        return [r for r in results if r.get("language") == language][:limit]

    def search_by_type(self, query: str, chunk_type: str, limit: int = 20) -> list:
        """Search within a specific chunk type (code, document, log, error_history)."""
        results = semantic_search.hybrid_search(query, limit=limit * 3)
        return [r for r in results if r.get("chunk_type") == chunk_type][:limit]

    def compare_repos(self, query: str, repos: list) -> dict:
        """Compare search results across repositories for the same query."""
        comparison = {}
        for repo in repos:
            results = semantic_search.hybrid_search(query, limit=10, repo=repo)
            comparison[repo] = {
                "result_count": len(results),
                "top_score": results[0]["final_score"] if results else 0,
                "top_results": results[:3],
            }
        return comparison

    def list_repos(self) -> list:
        """List all indexed repositories."""
        stats = knowledge_indexer.stats()
        return list(stats.get("by_repo", {}).keys())

    def repo_stats(self) -> dict:
        """Get indexing statistics for all repositories."""
        return knowledge_indexer.stats()


multi_repo_search = MultiRepositorySearch()
