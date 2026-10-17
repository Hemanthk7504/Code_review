"""Specialised LLM agents: Bug Detection, Security Analysis, Code Quality, Refactoring."""
import asyncio

from ..core.config import get_settings
from .llm import llm_client
from ..core.schemas import Category, Finding, Severity


JSON_RULES = """Reply with JSON only, in this exact shape:
{"findings": [{"line": <int>, "end_line": <int or null>, "severity": "critical|high|medium|low|info",
"title": "<short title>", "description": "<what is wrong and why>", "recommendation": "<how to fix>",
"code_snippet": "<exact text copied from the reported line>", "confidence": <0.0-1.0>}]}
Rules: report only real problems you can point to in the code. Use the line numbers shown.
Copy code_snippet exactly from the file. If there are no problems, return {"findings": []}."""

AGENTS: dict[str, tuple[Category, str]] = {
    "bug_detection": (Category.bug,
        "You are the Bug Detection agent in a code review system. Find logic errors, wrong conditions, "
        "off-by-one errors, unhandled edge cases, None/type errors, resource leaks and incorrect error handling."),
    "security_analysis": (Category.security,
        "You are the Security Analysis agent. Find security vulnerabilities: injection, unsafe deserialization, "
        "hard-coded secrets, weak crypto, path traversal, unsafe subprocess/eval use, missing validation."),
    "code_quality": (Category.quality,
        "You are the Code Quality agent. Find code smells, duplicated logic, dead code, unclear names, "
        "missing error handling, inefficient implementations and coding-standard (PEP 8) violations."),
    "refactoring": (Category.refactor,
        "You are the Refactoring agent. Suggest worthwhile refactors: extract functions, simplify nesting, "
        "remove duplication, improve structure. Only suggest changes that clearly improve the code."),
    "performance": (Category.performance,
        "You are the Performance & Resource Optimization agent. Identify algorithmic bottlenecks (O(N^2) loops), "
        "memory leaks, unclosed streams, blocking I/O in async code, unnecessary queries, and redundant allocations."),
    "test_coverage": (Category.quality,
        "You are the Testability & Robustness agent. Identify untested boundary conditions, unhandled None returns, "
        "missing input validation assertions, brittle assumptions, and unhandled failure paths."),
    "architecture": (Category.refactor,
        "You are the Architecture & Clean Code agent. Identify architectural anti-patterns, tight coupling, "
        "violation of Single Responsibility, god objects, circular dependencies, and poorly separated concerns."),
}


def numbered(content: str) -> str:
    limit = get_settings().max_file_chars
    text = content if len(content) <= limit else content[:limit]
    return "\n".join(f"{i:>4}: {line}" for i, line in enumerate(text.splitlines(), 1))


def _static_context(static_findings: list[Finding], limit: int = 15) -> str:
    if not static_findings:
        return "(no static-analysis findings)"
    rows = [f"line {f.line} [{','.join(f.sources)}] {f.rule_id}: {f.title}" for f in static_findings[:limit]]
    return "\n".join(rows)


def _coerce(path: str, agent: str, category: Category, item: dict) -> Finding | None:
    try:
        severity = Severity(str(item.get("severity", "low")).lower())
    except ValueError:
        severity = Severity.low
    try:
        line = max(1, int(item.get("line", 1)))
    except (TypeError, ValueError):
        return None
    end = item.get("end_line")
    try:
        end = int(end) if end else None
    except (TypeError, ValueError):
        end = None
    try:
        conf = min(1.0, max(0.0, float(item.get("confidence", 0.5))))
    except (TypeError, ValueError):
        conf = 0.5
    title = str(item.get("title", "")).strip()
    if not title:
        return None
    finding = Finding(
        file=path, line=line, end_line=end, category=category, severity=severity, title=title[:200],
        description=str(item.get("description", "")), recommendation=str(item.get("recommendation", "")),
        code_snippet=str(item.get("code_snippet", "")).strip(), sources=[agent],
        confidence=conf, rule_id="", evidence=[f"{agent}: {str(item.get('description', title))[:200]}"],
    )
    try:
        from ..utils.cwe_mapping import enrich_finding_taxonomy

        enrich_finding_taxonomy(finding)
    except Exception:

        pass
    return finding


async def run_agent(agent: str, path: str, content: str, static_findings: list[Finding]) -> list[Finding]:
    category, role = AGENTS[agent]
    user = (f"File: {path}\n\nStatic-analysis hints (may be incomplete):\n{_static_context(static_findings)}\n\n"
            f"Source code with line numbers:\n{numbered(content)}\n\n{JSON_RULES}")
    data = await llm_client.chat_json(role, user, task=f"agent:{agent}")
    if not isinstance(data, dict):
        return []
    out = []
    for item in data.get("findings", []) or []:
        if isinstance(item, dict):
            f = _coerce(path, agent, category, item)
            if f:
                out.append(f)
    return out


async def run_all_agents(path: str, content: str, static_findings: list[Finding]) -> list[Finding]:
    """Run all active specialist agents in parallel on one file."""
    if not llm_client.enabled:
        return []
    s = get_settings()
    active_agents = ["bug_detection", "security_analysis", "code_quality", "refactoring"]
    if getattr(s, "enable_performance_agent", True):
        active_agents.append("performance")
    if getattr(s, "enable_test_coverage_agent", True):
        active_agents.append("test_coverage")
    if getattr(s, "enable_architecture_agent", True):
        active_agents.append("architecture")

    results = await asyncio.gather(*(run_agent(a, path, content, static_findings) for a in active_agents))
    return [f for group in results for f in group]
