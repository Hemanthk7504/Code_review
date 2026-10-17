"""Merge duplicate findings from the static and AI pipelines and combine their evidence."""
import re
from difflib import SequenceMatcher

from ..core.schemas import SEVERITY_WEIGHT, Finding



_STOPWORDS = {"this", "that", "with", "from", "does", "code", "line", "function", "value", "when",
              "should", "used", "using", "which", "there", "have", "error", "argument", "type",
              "specified", "possibly", "consider", "unused", "issue", "problem"}
LINE_TOLERANCE = 2


def _keywords(f: Finding) -> set[str]:
    words = re.findall(r"[a-z]+", f"{f.title} {f.description}".lower())
    return {w for w in words if len(w) >= 4 and w not in _STOPWORDS}


def _similar(a: Finding, b: Finding) -> bool:
    """Two findings are duplicates when they sit on nearby lines AND talk about the same thing.

    Being near each other is not enough: an AI claim about a different problem must not
    be merged into (and then 'verified' by) an unrelated static finding."""
    if a.file != b.file or abs(a.line - b.line) > LINE_TOLERANCE:
        return False
    # two different rules from the same tool are different issues
    if a.rule_id and b.rule_id and a.rule_id != b.rule_id and set(a.sources) & set(b.sources):
        return False
    if SequenceMatcher(None, a.title.lower(), b.title.lower()).ratio() >= 0.6:
        return True
    return bool(_keywords(a) & _keywords(b))


def _merge(group: list[Finding]) -> Finding:
    rep = max(group, key=lambda f: (SEVERITY_WEIGHT[f.severity], f.confidence))
    merged = rep.model_copy(deep=True)
    sources, evidence = [], []
    miss = 1.0
    for f in group:
        for s in f.sources:
            if s not in sources:
                sources.append(s)
        for e in f.evidence:
            if e not in evidence:
                evidence.append(e)
        miss *= 1 - f.confidence
        if not merged.recommendation and f.recommendation:
            merged.recommendation = f.recommendation
        if not merged.rule_id and f.rule_id:
            merged.rule_id = f.rule_id
        if not merged.code_snippet and f.code_snippet:
            merged.code_snippet = f.code_snippet
    merged.sources = sources
    merged.evidence = evidence
    if len(group) > 1:
        merged.confidence = min(0.98, 1 - miss)
        if merged.static_sources and merged.ai_sources:
            merged.evidence.append("Corroborated by both static analysis and AI analysis.")
    return merged


def consolidate(findings: list[Finding]) -> list[Finding]:
    ordered = sorted(findings, key=lambda f: (f.file, f.line))
    groups: list[list[Finding]] = []
    for f in ordered:
        for g in groups:
            if all(_similar(f, m) for m in g):  # complete linkage: no chaining through a third finding
                g.append(f)
                break
        else:
            groups.append([f])
    return [_merge(g) for g in groups]
