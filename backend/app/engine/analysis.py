"""Multilingual and Python Analysis Pipeline:
Static Scanners + Multi-Agent AI Specialists -> Consolidation -> Risk Scoring -> Evidence-Based Self-Verification.
"""
import asyncio
import logging
from typing import Tuple

from .agents import run_all_agents
from .consolidation import consolidate
from .language import Language, detect_language
from .risk import apply_risk
from ..core.schemas import FileInput, Finding
from ..scanners.multilingual import scan_multilingual_file
from ..scanners.static_analysis import analyze_file
from .verifier import verify_findings


log = logging.getLogger(__name__)


def is_python(path: str) -> bool:
    info = detect_language(path)
    return info.language == Language.PYTHON


async def _analyze_one(f: FileInput) -> list[Finding]:
    info = detect_language(f.path, f.content)
    static_findings: list[Finding] = []

    if info.language == Language.PYTHON:
        static_findings = await analyze_file(f.path, f.content)
    elif info.is_supported:
        static_findings = scan_multilingual_file(f.path, f.content)

    # Dispatched AI specialist agents (Security, Logic Bug, Quality, Performance)
    ai_findings = await run_all_agents(f.path, f.content, static_findings)
    return static_findings + ai_findings


async def analyze_files(files: list[FileInput]) -> Tuple[list[Finding], list[str]]:
    """Analyze source files across supported programming languages.

    Returns:
        (findings, skipped_files): List of verified findings and list of skipped unsupported files.
    """
    supported_files: list[FileInput] = []
    skipped_files: list[str] = []

    for f in files:
        info = detect_language(f.path, f.content)
        if info.is_supported:
            supported_files.append(f)
        else:
            skipped_files.append(f.path)

    if not supported_files:
        return [], skipped_files

    groups = await asyncio.gather(*(_analyze_one(f) for f in supported_files))
    raw = [x for g in groups for x in g]
    merged = consolidate(raw)
    apply_risk(merged, supported_files)
    await verify_findings(merged, {f.path: f.content for f in supported_files})
    return merged, skipped_files
