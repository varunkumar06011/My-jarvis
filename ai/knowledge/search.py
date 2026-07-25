import re
import math
import hashlib
from collections import Counter, defaultdict
from typing import Optional

from ai.knowledge.indexer import knowledge_indexer


class SemanticSearch:
    """Semantic search using TF-IDF similarity and keyword matching.
    Provides both semantic and hybrid search capabilities."""

    def __init__(self):
        self._tf_cache: dict[str, Counter] = {}
        self._idf_cache: dict[str, float] = {}
        self._doc_lengths: dict[str, int] = {}
        self._inverted_index: dict[str, list[str]] = defaultdict(list)
        self._built = False

    def build_index(self):
        """Build TF-IDF index from all indexed entries."""
        self._tf_cache.clear()
        self._idf_cache.clear()
        self._doc_lengths.clear()
        self._inverted_index.clear()

        entries = knowledge_indexer._entries
        if not entries:
            return

        doc_freq = defaultdict(int)
        total_docs = len(entries)

        for entry in entries:
            doc_id = entry.id
            tokens = self._tokenize(entry.content)
            tf = Counter(tokens)
            self._tf_cache[doc_id] = tf
            self._doc_lengths[doc_id] = len(tokens)

            for term in set(tokens):
                doc_freq[term] += 1
                self._inverted_index[term].append(doc_id)

        for term, df in doc_freq.items():
            self._idf_cache[term] = math.log((total_docs + 1) / (df + 1)) + 1

        self._built = True

    def semantic_search(self, query: str, limit: int = 20, repo: str = None) -> list:
        """Semantic search using TF-IDF cosine similarity."""
        if not self._built:
            self.build_index()

        query_tokens = self._tokenize(query)
        query_tf = Counter(query_tokens)
        query_vec = {}
        for term, count in query_tf.items():
            idf = self._idf_cache.get(term, 0)
            if idf > 0:
                query_vec[term] = count * idf

        query_norm = math.sqrt(sum(v ** 2 for v in query_vec.values()))
        if query_norm == 0:
            return self._keyword_fallback(query, limit, repo)

        candidate_ids = set()
        for token in query_tokens:
            candidate_ids.update(self._inverted_index.get(token, []))

        scores = []
        for doc_id in candidate_ids:
            entry = self._find_entry(doc_id)
            if entry is None:
                continue
            if repo and entry.repo != repo:
                continue

            tf = self._tf_cache.get(doc_id, Counter())
            doc_vec = {}
            for term, count in tf.items():
                idf = self._idf_cache.get(term, 0)
                if idf > 0:
                    doc_vec[term] = count * idf

            doc_norm = math.sqrt(sum(v ** 2 for v in doc_vec.values()))
            if doc_norm == 0:
                continue

            dot_product = sum(query_vec.get(t, 0) * doc_vec.get(t, 0) for t in query_vec)
            similarity = dot_product / (query_norm * doc_norm)

            if similarity > 0:
                scores.append((doc_id, similarity, entry))

        scores.sort(key=lambda x: x[1], reverse=True)

        return [
            {
                **entry.to_dict(),
                "score": round(score, 4),
            }
            for _, score, entry in scores[:limit]
        ]

    def hybrid_search(self, query: str, limit: int = 20, repo: str = None) -> list:
        """Hybrid search combining semantic similarity with exact keyword matching."""
        semantic_results = self.semantic_search(query, limit=limit * 2, repo=repo)
        keyword_results = self._keyword_fallback(query, limit=limit * 2, repo=repo)

        combined: dict[str, dict] = {}

        for result in semantic_results:
            doc_id = result["id"]
            combined[doc_id] = {**result, "semantic_score": result["score"], "keyword_score": 0}

        for result in keyword_results:
            doc_id = result["id"]
            if doc_id in combined:
                combined[doc_id]["keyword_score"] = result["score"]
            else:
                combined[doc_id] = {**result, "semantic_score": 0, "keyword_score": result["score"]}

        for item in combined.values():
            item["final_score"] = round(item["semantic_score"] * 0.7 + item["keyword_score"] * 0.3, 4)

        results = sorted(combined.values(), key=lambda x: x["final_score"], reverse=True)
        return results[:limit]

    def _keyword_fallback(self, query: str, limit: int, repo: str = None) -> list:
        """Exact keyword matching fallback."""
        keywords = self._tokenize(query)
        results = []

        for entry in knowledge_indexer._entries:
            if repo and entry.repo != repo:
                continue

            content_lower = entry.content.lower()
            score = 0
            for kw in keywords:
                count = content_lower.count(kw)
                score += count

            if score > 0:
                results.append({
                    **entry.to_dict(),
                    "score": round(score / max(len(entry.content), 1) * 100, 4),
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def _find_entry(self, doc_id: str):
        for entry in knowledge_indexer._entries:
            if entry.id == doc_id:
                return entry
        return None

    def _tokenize(self, text: str) -> list:
        text = text.lower()
        tokens = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', text)
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "must", "can", "this",
            "that", "these", "those", "i", "you", "he", "she", "it",
            "we", "they", "what", "which", "who", "when", "where", "why",
            "how", "all", "each", "every", "both", "few", "more", "most",
            "other", "some", "such", "no", "nor", "not", "only", "own",
            "same", "so", "than", "too", "very", "s", "t", "just",
            "don", "now", "in", "on", "at", "to", "for", "of", "with",
            "by", "from", "as", "or", "if", "but", "and", "about",
        }
        return [t for t in tokens if t not in stop_words and len(t) > 1]


semantic_search = SemanticSearch()
