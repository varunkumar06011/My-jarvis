from pathlib import Path
from typing import Optional


class LanguageInfo:
    """Information about a detected language in the repository."""

    def __init__(self, name: str, extensions: list, file_count: int = 0, total_lines: int = 0):
        self.name = name
        self.extensions = extensions
        self.file_count = file_count
        self.total_lines = total_lines

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "extensions": self.extensions,
            "file_count": self.file_count,
            "total_lines": self.total_lines,
        }


LANGUAGE_MAP = {
    ".py": ("Python", ["py"]),
    ".js": ("JavaScript", ["js"]),
    ".jsx": ("JavaScript", ["js", "jsx"]),
    ".mjs": ("JavaScript", ["js", "mjs"]),
    ".cjs": ("JavaScript", ["js", "cjs"]),
    ".ts": ("TypeScript", ["ts"]),
    ".tsx": ("TypeScript", ["ts", "tsx"]),
    ".java": ("Java", ["java"]),
    ".cs": ("C#", ["cs"]),
    ".go": ("Go", ["go"]),
    ".rs": ("Rust", ["rs"]),
    ".c": ("C/C++", ["c"]),
    ".cpp": ("C/C++", ["cpp"]),
    ".cc": ("C/C++", ["cc"]),
    ".cxx": ("C/C++", ["cxx"]),
    ".h": ("C/C++", ["h"]),
    ".hpp": ("C/C++", ["hpp"]),
    ".php": ("PHP", ["php"]),
    ".html": ("HTML/CSS", ["html"]),
    ".htm": ("HTML/CSS", ["html"]),
    ".css": ("HTML/CSS", ["css"]),
    ".scss": ("HTML/CSS", ["scss"]),
    ".less": ("HTML/CSS", ["less"]),
    ".sql": ("SQL", ["sql"]),
    ".yaml": ("YAML", ["yaml"]),
    ".yml": ("YAML", ["yaml"]),
    ".json": ("JSON", ["json"]),
    ".md": ("Markdown", ["md"]),
    ".markdown": ("Markdown", ["md"]),
}

EXCLUDE_DIRS = {
    "venv", "__pycache__", ".git", "node_modules", ".hg", ".svn",
    "dist", "build", ".next", ".nuxt", "target", "bin", "obj",
    ".idea", ".vscode", "coverage", ".cache", "assets",
}


class LanguageDetector:
    """Detects all programming languages in a repository and counts files/lines."""

    def __init__(self, root: str = "."):
        self.root = Path(root).resolve()

    def detect(self) -> dict:
        languages: dict[str, LanguageInfo] = {}

        for filepath in self._walk():
            ext = filepath.suffix.lower()
            if ext not in LANGUAGE_MAP:
                continue

            lang_name, extensions = LANGUAGE_MAP[ext]

            if lang_name not in languages:
                languages[lang_name] = LanguageInfo(lang_name, extensions)

            languages[lang_name].file_count += 1

            try:
                with filepath.open(encoding="utf-8", errors="replace") as f:
                    line_count = sum(1 for _ in f)
                languages[lang_name].total_lines += line_count
            except Exception:
                pass

        sorted_langs = sorted(languages.values(), key=lambda l: l.total_lines, reverse=True)

        return {
            "languages": [l.to_dict() for l in sorted_langs],
            "primary_language": sorted_langs[0].name if sorted_langs else None,
            "total_files": sum(l.file_count for l in sorted_langs),
            "total_lines": sum(l.total_lines for l in sorted_langs),
        }

    def _walk(self):
        for item in self.root.rglob("*"):
            if not item.is_file():
                continue
            if any(part in EXCLUDE_DIRS for part in item.parts):
                continue
            yield item

    def get_files_by_language(self, language: str) -> list:
        """Return all file paths for a given language name."""
        files = []
        for filepath in self._walk():
            ext = filepath.suffix.lower()
            if ext not in LANGUAGE_MAP:
                continue
            lang_name, _ = LANGUAGE_MAP[ext]
            if lang_name == language:
                files.append(str(filepath.relative_to(self.root)).replace("\\", "/"))
        return files


language_detector = LanguageDetector()
