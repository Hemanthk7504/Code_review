"""Full analysis cycle for a set of files:
static + AI pipelines (parallel) -> consolidation -> risk scoring -> self-verification."""
import asyncio

from .agents import run_all_agents
from .consolidation import consolidate
from .risk import apply_risk
from ..core.schemas import FileInput, Finding
from ..scanners.static_analysis import analyze_file
from .verifier import verify_findings



def is_python(path: str) -> bool:
    return path.endswith(".py")


async def _analyze_one(f: FileInput) -> list[Finding]:
    static_findings = await analyze_file(f.path, f.content)
    ai_findings = await run_all_agents(f.path, f.content, static_findings)
    return static_findings + ai_findings


async def analyze_files(files: list[FileInput]) -> tuple[list[Finding], list[str]]:
    py_files = [f for f in files if is_python(f.path)]
    skipped = [f.path for f in files if not is_python(f.path)]
    groups = await asyncio.gather(*(_analyze_one(f) for f in py_files))
    raw = [x for g in groups for x in g]
    merged = consolidate(raw)
    apply_risk(merged, py_files)
    await verify_findings(merged, {f.path: f.content for f in py_files})
    return merged, skipped
