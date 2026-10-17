"""Second analysis + verification cycle on revised code.

A revision is accepted only if: the code still parses, the targeted issues are resolved,
no new verified issues appear, and the overall risk goes down.
"""
import ast
from collections import Counter
from typing import Optional

from ..engine.analysis import analyze_files
from ..core.config import get_settings
from ..engine.risk import overall_risk
from ..core.schemas import FileInput, Finding, Revision, RevisionValidation, VerificationStatus



def _scopes(code: str) -> list[tuple[int, int, str]]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.append((node.lineno, node.end_lineno or node.lineno, node.name))
    return out


def _scope_at(scopes: list[tuple[int, int, str]], line: int) -> str:
    best: Optional[tuple[int, int, str]] = None
    for lo, hi, name in scopes:
        if lo <= line <= hi and (best is None or lo >= best[0]):
            best = (lo, hi, name)
    return best[2] if best else "<module>"


def signature(f: Finding, scopes: list[tuple[int, int, str]]) -> tuple[str, str, str]:
    """A signature that stays stable when line numbers shift after a fix."""
    rule = f.rule_id or f"ai:{f.category.value}"
    return (f.category.value, rule, _scope_at(scopes, f.line))


async def validate_revision(revision: Revision, original_findings: list[Finding]) -> RevisionValidation:
    s = get_settings()
    path = revision.path
    file_findings = [f for f in original_findings if f.file == path]
    targeted = [f for f in file_findings if f.id in set(revision.targeted_finding_ids)
                and f.verification == VerificationStatus.verified]
    baseline = [f for f in file_findings if f.verification != VerificationStatus.rejected]
    risk_before = overall_risk(baseline)

    reasons: list[str] = []
    if not revision.syntax_ok:
        return RevisionValidation(
            path=path, accepted=False, syntax_ok=False, targeted=len(targeted), resolved=0,
            resolution_ratio=0.0, unresolved_finding_ids=[f.id for f in targeted],
            risk_before=risk_before, risk_after=risk_before,
            reasons=["Revised code has a syntax error."])

    after_all, _ = await analyze_files([FileInput(path=path, content=revision.revised_code)])
    after_live = [f for f in after_all if f.verification != VerificationStatus.rejected]
    after_verified = [f for f in after_all if f.verification == VerificationStatus.verified]
    risk_after = overall_risk(after_live)

    old_scopes, new_scopes = _scopes(revision.original_code), _scopes(revision.revised_code)
    remaining = Counter(signature(f, new_scopes) for f in after_verified)

    # resolved = a targeted issue whose signature no longer appears in the revised code
    resolved, unresolved = 0, []
    for f in targeted:
        sig = signature(f, old_scopes)
        if remaining[sig] > 0:
            remaining[sig] -= 1
            unresolved.append(f.id)
        else:
            resolved += 1

    # new issue = verified finding in the revised code that did not exist before
    known = Counter(signature(f, old_scopes) for f in baseline)
    new_findings: list[Finding] = []
    for f in after_verified:
        sig = signature(f, new_scopes)
        if known[sig] > 0:
            known[sig] -= 1
        else:
            new_findings.append(f)

    ratio = round(resolved / len(targeted), 3) if targeted else 1.0
    if ratio < s.min_resolution_ratio:
        reasons.append(f"Only {resolved}/{len(targeted)} targeted issues were resolved "
                       f"(need ratio {s.min_resolution_ratio}).")
    if len(new_findings) > s.max_new_issues:
        reasons.append(f"{len(new_findings)} new verified issue(s) were introduced "
                       f"(allowed {s.max_new_issues}).")
    if risk_before > 0 and risk_after >= risk_before:
        reasons.append(f"Overall risk did not go down ({risk_before} -> {risk_after}).")

    accepted = not reasons
    if accepted:
        reasons.append("All validation checks passed.")
    return RevisionValidation(
        path=path, accepted=accepted, syntax_ok=True, targeted=len(targeted), resolved=resolved,
        resolution_ratio=ratio, unresolved_finding_ids=unresolved, new_findings=new_findings,
        risk_before=risk_before, risk_after=risk_after, reasons=reasons)
