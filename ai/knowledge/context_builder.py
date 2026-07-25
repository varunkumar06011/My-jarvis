from typing import Optional

from ai.knowledge.indexer import knowledge_indexer
from ai.knowledge.search import semantic_search
from ai.knowledge.multi_repo import multi_repo_search


class ContextBuilder:
    """Automatically assembles relevant context before querying the LLM.
    Uses semantic search to find the most relevant code, docs, and history,
    then structures them into a context window for the LLM."""

    MAX_CONTEXT_TOKENS = 8000
    APPROX_CHARS_PER_TOKEN = 4

    def build_context(self, query: str, repo: str = None, max_chunks: int = 10) -> dict:
        """Build a context payload for an LLM query."""
        results = semantic_search.hybrid_search(query, limit=max_chunks * 2, repo=repo)

        if not results:
            return {
                "query": query,
                "context": "",
                "sources": [],
                "chunk_count": 0,
            }

        selected = []
        total_chars = 0
        max_chars = self.MAX_CONTEXT_TOKENS * self.APPROX_CHARS_PER_TOKEN

        for result in results:
            content = result.get("content", "")
            chunk_chars = len(content)
            if total_chars + chunk_chars > max_chars:
                remaining = max_chars - total_chars
                if remaining > 200:
                    content = content[:remaining] + "\n... [truncated]"
                    selected.append({**result, "content": content})
                    total_chars += len(content)
                break
            selected.append(result)
            total_chars += chunk_chars

        context_parts = []
        for item in selected:
            source_label = f"[{item.get('repo', '?')}] {item.get('file', '?')}"
            if item.get("line_start"):
                source_label += f":{item['line_start']}-{item.get('line_end', '')}"
            context_parts.append(f"--- {source_label} ({item.get('language', '?')}) ---\n{item.get('content', '')}")

        context_text = "\n\n".join(context_parts)

        return {
            "query": query,
            "context": context_text,
            "sources": [
                {
                    "repo": s.get("repo"),
                    "file": s.get("file"),
                    "line_start": s.get("line_start"),
                    "line_end": s.get("line_end"),
                    "language": s.get("language"),
                    "score": s.get("final_score", s.get("score", 0)),
                }
                for s in selected
            ],
            "chunk_count": len(selected),
            "total_chars": total_chars,
            "estimated_tokens": total_chars // self.APPROX_CHARS_PER_TOKEN,
        }

    def build_context_with_history(self, query: str, conversation_history: list = None,
                                    repo: str = None, max_chunks: int = 8) -> dict:
        """Build context that includes conversation history for continuity."""
        base_context = self.build_context(query, repo=repo, max_chunks=max_chunks)

        history_text = ""
        if conversation_history:
            history_parts = []
            for msg in conversation_history[-10:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_parts.append(f"[{role}]: {content}")
            history_text = "\n".join(history_parts)

        return {
            **base_context,
            "conversation_history": history_text,
            "full_context": f"{history_text}\n\n--- Relevant Code Context ---\n{base_context['context']}" if history_text else base_context["context"],
        }

    def build_code_review_context(self, file_path: str, repo: str = None) -> dict:
        """Build context specifically for code review of a file."""
        entries = knowledge_indexer.get_entries(repo=repo, file=file_path)

        if not entries:
            return {"file": file_path, "context": "", "sources": []}

        related_query = " ".join(entries[0].get("symbols", []))
        related = []
        if related_query:
            related = semantic_search.semantic_search(related_query, limit=5, repo=repo)
            related = [r for r in related if r.get("file") != file_path]

        context_parts = []
        for entry in entries:
            context_parts.append(f"--- {entry['file']}:{entry.get('line_start', 0)} ---\n{entry['content']}")

        for r in related:
            context_parts.append(f"--- Related: {r['file']}:{r.get('line_start', 0)} ---\n{r['content'][:1000]}")

        return {
            "file": file_path,
            "context": "\n\n".join(context_parts),
            "sources": [
                {"file": e["file"], "line_start": e.get("line_start"), "line_end": e.get("line_end")}
                for e in entries
            ] + [
                {"file": r["file"], "line_start": r.get("line_start"), "related": True}
                for r in related
            ],
        }


context_builder = ContextBuilder()
