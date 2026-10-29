"""Multilingual and Python Analysis Pipeline:
Static Scanners + Multi-Agent AI Specialists -> Consolidation -> Risk Scoring -> Evidence-Based Self-Verification.
"""
import asyncio
import logging
from typing import Callable, Optional, Tuple

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


async def _static_scan_one(f: FileInput) -> list[Finding]:
    info = detect_language(f.path, f.content)
    if info.language == Language.PYTHON:
        return await analyze_file(f.path, f.content)
    elif info.is_supported:
        return scan_multilingual_file(f.path, f.content)
    return []


async def analyze_files(files: list[FileInput], on_progress: Optional[Callable[[str, int, str], None]] = None) -> Tuple[list[Finding], list[str]]:
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

    if on_progress:
        on_progress("Static SAST", 35, f"Running Bandit SAST, Pylint AST, and Radon on {len(supported_files)} file(s)...")

    static_groups = await asyncio.gather(*(_static_scan_one(f) for f in supported_files))

    if on_progress:
        on_progress("AI Specialists", 50, f"Dispatching cognitive specialist agents (Security, Bug, Quality) across {len(supported_files)} file(s)...")

    ai_groups = await asyncio.gather(*(run_all_agents(f.path, f.content, sf) for f, sf in zip(supported_files, static_groups)))
    raw = [x for g in list(static_groups) + list(ai_groups) for x in g]

    if on_progress:
        on_progress("Consolidating", 60, f"Corroborating findings across engines and applying CVSS/CWE risk scores...")

    merged = consolidate(raw)
    apply_risk(merged, supported_files)

    if on_progress:
        on_progress("Self-Verify", 70, f"Skeptical verification: auditing {len(merged)} claim(s) against AST context...")

    await verify_findings(merged, {f.path: f.content for f in supported_files})
    return merged, skipped_files
