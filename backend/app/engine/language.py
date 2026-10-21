"""Multilingual Language Detection and Registry.

Provides automatic language identification by file extension, shebang, and content heuristics,
along with support status and parser mapping.
"""
import os
import re
from enum import Enum
from pathlib import Path
from typing import Optional


class Language(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    JAVA = "java"
    C_CPP = "c_cpp"
    RUBY = "ruby"
    PHP = "php"
    CSHARP = "csharp"
    UNSUPPORTED = "unsupported"
    BINARY = "binary"


LANGUAGE_EXTENSIONS: dict[str, Language] = {
    # Python
    ".py": Language.PYTHON,
    ".pyw": Language.PYTHON,
    ".pyi": Language.PYTHON,
    # JavaScript
    ".js": Language.JAVASCRIPT,
    ".jsx": Language.JAVASCRIPT,
    ".mjs": Language.JAVASCRIPT,
    ".cjs": Language.JAVASCRIPT,
    # TypeScript
    ".ts": Language.TYPESCRIPT,
    ".tsx": Language.TYPESCRIPT,
    # Go
    ".go": Language.GO,
    # Java
    ".java": Language.JAVA,
    # C / C++
    ".c": Language.C_CPP,
    ".cpp": Language.C_CPP,
    ".cc": Language.C_CPP,
    ".cxx": Language.C_CPP,
    ".h": Language.C_CPP,
    ".hpp": Language.C_CPP,
    # Ruby
    ".rb": Language.RUBY,
    # PHP
    ".php": Language.PHP,
    # C#
    ".cs": Language.CSHARP,
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".o", ".a",
    ".zip", ".tar", ".gz", ".7z", ".rar", ".bz2",
    ".pdf", ".docx", ".xlsx", ".pptx", ".parquet", ".db", ".sqlite",
    ".pyc", ".pyo", ".class", ".jar", ".war"
}

SHEBANG_MAP = [
    (re.compile(r"^#!\s*/.*\b(python|python3)\b"), Language.PYTHON),
    (re.compile(r"^#!\s*/.*\b(node|nodejs)\b"), Language.JAVASCRIPT),
    (re.compile(r"^#!\s*/.*\b(ts-node|deno|bun)\b"), Language.TYPESCRIPT),
    (re.compile(r"^#!\s*/.*\b(ruby)\b"), Language.RUBY),
    (re.compile(r"^#!\s*/.*\b(php)\b"), Language.PHP),
]


class LanguageInfo:
    def __init__(self, language: Language, display_name: str, is_supported: bool, reason: str = ""):
        self.language = language
        self.display_name = display_name
        self.is_supported = is_supported
        self.reason = reason

    def __repr__(self) -> str:
        return f"<LanguageInfo language={self.language.value} supported={self.is_supported}>"


DISPLAY_NAMES = {
    Language.PYTHON: "Python",
    Language.JAVASCRIPT: "JavaScript",
    Language.TYPESCRIPT: "TypeScript",
    Language.GO: "Go",
    Language.JAVA: "Java",
    Language.C_CPP: "C / C++",
    Language.RUBY: "Ruby",
    Language.PHP: "PHP",
    Language.CSHARP: "C#",
    Language.UNSUPPORTED: "Unsupported Language",
    Language.BINARY: "Binary File",
}


def detect_language(path: str, content: str = "") -> LanguageInfo:
    """Detect programming language using file extension, shebang, and content heuristics."""
    ext = Path(path).suffix.lower()

    if ext in BINARY_EXTENSIONS:
        return LanguageInfo(Language.BINARY, "Binary File", False, f"Binary or media file format ({ext}) is not supported for source code review.")

    if ext in LANGUAGE_EXTENSIONS:
        lang = LANGUAGE_EXTENSIONS[ext]
        return LanguageInfo(lang, DISPLAY_NAMES[lang], True)

    # Check shebang line if text content is provided
    if content:
        first_line = content.splitlines()[0] if content.splitlines() else ""
        if first_line.startswith("#!"):
            for pattern, lang in SHEBANG_MAP:
                if pattern.search(first_line):
                    return LanguageInfo(lang, DISPLAY_NAMES[lang], True)

    # Non-code files (documentation, config files)
    if ext in {".txt", ".md", ".rst", ".doc"}:
        return LanguageInfo(Language.UNSUPPORTED, "Text Document", False, f"Plain text / documentation file format ({ext}) is not source code.")

    if ext in {".json", ".yaml", ".yml", ".xml", ".toml", ".ini", ".env"}:
        return LanguageInfo(Language.UNSUPPORTED, "Configuration File", False, f"Structured data / configuration file ({ext}) is not directly reviewed as executable source code.")

    return LanguageInfo(Language.UNSUPPORTED, f"Unknown ({ext or 'no extension'})", False,
                        f"Unsupported programming language or file extension '{ext or path}'.")
