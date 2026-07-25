import json
import hashlib
import time
import re
from pathlib import Path
from typing import Optional
from collections import defaultdict

from core.event_bus import bus
from ai.repo.languages import LANGUAGE_MAP, EXCLUDE_DIRS

INDEX_DIR = Path("data/knowledge_index")
INDEX_DIR.mkdir(parents=True, exist_ok=True)


class IndexEntry:
    __slots__ = ("id", "repo", "file", "language", "content", "chunk_type",
                 "line_start", "line_end", "symbols", "hash", "indexed_at", "size")

    def __init__(self, repo: str, file: str, language: str, content: str,
                 chunk_type: str = "code", line_start: int = 0, line_end: int = 0,
                 symbols: list = None):
        self.id = hashlib.md5(f"{repo}:{file}:{line_start}:{chunk_type}".encode()).hexdigest()[:16]
        self.repo = repo
        self.file = file
        self.language = language
        self.content = content
        self.chunk_type = chunk_type
        self.line_start = line_start
        self.line_end = line_end
        self.symbols = symbols or []
        self.hash = hashlib.md5(content.encode()).hexdigest()
        self.indexed_at = time.time()
        self.size = len(content)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "repo": self.repo,
            "file": self.file,
            "language": self.language,
            "content": self.content[:2000],
            "chunk_type": self.chunk_type,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "symbols": self.symbols,
            "hash": self.hash,
            "indexed_at": self.indexed_at,
            "size": self.size,
        }


class KnowledgeIndexer:
    """Indexes source code, documentation, APIs, SQL, config, markdown,
    architecture, logs, and error history into searchable chunks."""

    INDEXABLE_EXTENSIONS = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".jsx": "javascript", ".tsx": "typescript",
        ".java": "java", ".cs": "csharp", ".go": "go",
        ".rs": "rust", ".c": "c", ".cpp": "cpp", ".h": "c",
        ".php": "php", ".html": "html", ".css": "css",
        ".sql": "sql", ".yaml": "yaml", ".yml": "yaml",
        ".json": "json", ".md": "markdown", ".txt": "text",
        ".env": "dotenv", ".toml": "toml", ".cfg": "ini",
        ".ini": "ini", ".xml": "xml",
    }

    CHUNK_SIZE = 80
    CHUNK_OVERLAP = 10

    def __init__(self):
        self._entries: list[IndexEntry] = []
        self._file_hashes: dict[str, str] = {}
        self._repo_hashes: dict[str, dict[str, str]] = defaultdict(dict)
        self._lock = False

    def index_repository(self, root: str, repo_name: str = None) -> dict:
        """Index an entire repository."""
        root_path = Path(root).resolve()
        repo_name = repo_name or root_path.name

        indexed_files = 0
        skipped_files = 0
        total_chunks = 0

        for filepath in self._walk(root_path):
            rel = str(filepath.relative_to(root_path)).replace("\\", "/")
            ext = filepath.suffix.lower()

            if ext not in self.INDEXABLE_EXTENSIONS:
                continue

            language = self.INDEXABLE_EXTENSIONS[ext]

            try:
                content = filepath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                skipped_files += 1
                continue

            file_hash = hashlib.md5(content.encode()).hexdigest()

            if rel in self._repo_hashes.get(repo_name, {}):
                if self._repo_hashes[repo_name][rel] == file_hash:
                    skipped_files += 1
                    continue

            self._repo_hashes[repo_name][rel] = file_hash

            chunks = self._chunk_content(content, language)

            for chunk in chunks:
                entry = IndexEntry(
                    repo=repo_name,
                    file=rel,
                    language=language,
                    content=chunk["content"],
                    chunk_type=chunk["type"],
                    line_start=chunk["line_start"],
                    line_end=chunk["line_end"],
                    symbols=chunk.get("symbols", []),
                )
                self._entries.append(entry)
                total_chunks += 1

            indexed_files += 1

        self._index_logs_and_errors(repo_name, root_path)

        bus.publish("RepositoryIndexed", {
            "repo": repo_name,
            "files": indexed_files,
            "chunks": total_chunks,
            "skipped": skipped_files,
        })

        return {
            "repo": repo_name,
            "indexed_files": indexed_files,
            "skipped_files": skipped_files,
            "total_chunks": total_chunks,
            "total_entries": len(self._entries),
        }

    def _walk(self, root: Path):
        for filepath in root.rglob("*"):
            if not filepath.is_file():
                continue
            if any(part in EXCLUDE_DIRS for part in filepath.parts):
                continue
            if filepath.stat().st_size > 500_000:
                continue
            yield filepath

    def _chunk_content(self, content: str, language: str) -> list:
        lines = content.split("\n")
        chunks = []

        if language in ("markdown", "text", "json", "yaml", "toml", "ini", "xml", "dotenv"):
            chunk_size = self.CHUNK_SIZE * 2
            for i in range(0, len(lines), chunk_size):
                chunk_lines = lines[i:i + chunk_size]
                chunks.append({
                    "content": "\n".join(chunk_lines),
                    "type": "document",
                    "line_start": i + 1,
                    "line_end": i + len(chunk_lines),
                })
            return chunks

        current_chunk = []
        chunk_start = 1
        current_class = None
        current_func = None
        symbols = []

        for idx, line in enumerate(lines, 1):
            current_chunk.append(line)

            stripped = line.strip()

            class_match = re.match(r'(?:class|public\s+class|private\s+class|protected\s+class)\s+(\w+)', stripped)
            if class_match:
                current_class = class_match.group(1)
                symbols.append(f"class:{current_class}")

            func_patterns = [
                r'def\s+(\w+)',
                r'function\s+(\w+)',
                r'(?:public|private|protected|static)\s+(?:\w+\s+)?(\w+)\s*\(',
                r'const\s+(\w+)\s*=\s*(?:async\s+)?\(',
                r'func\s+(\w+)',
                r'fn\s+(\w+)',
            ]
            for fp in func_patterns:
                func_match = re.match(fp, stripped)
                if func_match:
                    current_func = func_match.group(1)
                    symbols.append(f"func:{current_func}")
                    break

            if len(current_chunk) >= self.CHUNK_SIZE:
                chunks.append({
                    "content": "\n".join(current_chunk),
                    "type": "code",
                    "line_start": chunk_start,
                    "line_end": idx,
                    "symbols": symbols[:],
                })
                overlap_lines = current_chunk[-self.CHUNK_OVERLAP:]
                current_chunk = list(overlap_lines)
                chunk_start = idx - self.CHUNK_OVERLAP + 1
                symbols = []

        if current_chunk:
            chunks.append({
                "content": "\n".join(current_chunk),
                "type": "code",
                "line_start": chunk_start,
                "line_end": len(lines),
                "symbols": symbols,
            })

        return chunks

    def _index_logs_and_errors(self, repo_name: str, root: Path):
        log_dirs = [root / "logs", root / "data" / "telemetry"]
        for log_dir in log_dirs:
            if not log_dir.is_dir():
                continue
            for filepath in log_dir.glob("*.jsonl"):
                try:
                    content = filepath.read_text(encoding="utf-8", errors="replace")
                    lines = content.strip().split("\n")
                    for i in range(0, len(lines), 50):
                        chunk_lines = lines[i:i + 50]
                        entry = IndexEntry(
                            repo=repo_name,
                            file=str(filepath.relative_to(root)).replace("\\", "/"),
                            language="log",
                            content="\n".join(chunk_lines),
                            chunk_type="log",
                            line_start=i + 1,
                            line_end=i + len(chunk_lines),
                        )
                        self._entries.append(entry)
                except Exception:
                    pass

            for filepath in log_dir.glob("*.json"):
                try:
                    content = filepath.read_text(encoding="utf-8", errors="replace")
                    entry = IndexEntry(
                        repo=repo_name,
                        file=str(filepath.relative_to(root)).replace("\\", "/"),
                        language="log",
                        content=content[:5000],
                        chunk_type="error_history",
                    )
                    self._entries.append(entry)
                except Exception:
                    pass

    def get_entries(self, repo: str = None, file: str = None,
                    language: str = None, chunk_type: str = None) -> list:
        results = []
        for entry in self._entries:
            if repo and entry.repo != repo:
                continue
            if file and entry.file != file:
                continue
            if language and entry.language != language:
                continue
            if chunk_type and entry.chunk_type != chunk_type:
                continue
            results.append(entry.to_dict())
        return results

    def stats(self) -> dict:
        repos = set(e.repo for e in self._entries)
        by_repo = defaultdict(int)
        by_language = defaultdict(int)
        by_type = defaultdict(int)

        for e in self._entries:
            by_repo[e.repo] += 1
            by_language[e.language] += 1
            by_type[e.chunk_type] += 1

        return {
            "total_entries": len(self._entries),
            "total_repos": len(repos),
            "by_repo": dict(by_repo),
            "by_language": dict(by_language),
            "by_type": dict(by_type),
        }

    def clear(self, repo: str = None):
        if repo:
            self._entries = [e for e in self._entries if e.repo != repo]
            if repo in self._repo_hashes:
                del self._repo_hashes[repo]
        else:
            self._entries.clear()
            self._repo_hashes.clear()

    def persist(self):
        """Persist index to disk."""
        filepath = INDEX_DIR / "index.json"
        data = [e.to_dict() for e in self._entries]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self):
        """Load index from disk."""
        filepath = INDEX_DIR / "index.json"
        if not filepath.exists():
            return
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            self._entries.clear()
            for item in data:
                entry = IndexEntry(
                    repo=item["repo"],
                    file=item["file"],
                    language=item["language"],
                    content=item["content"],
                    chunk_type=item["chunk_type"],
                    line_start=item.get("line_start", 0),
                    line_end=item.get("line_end", 0),
                    symbols=item.get("symbols", []),
                )
                entry.indexed_at = item.get("indexed_at", time.time())
                self._entries.append(entry)
        except Exception:
            pass


knowledge_indexer = KnowledgeIndexer()
