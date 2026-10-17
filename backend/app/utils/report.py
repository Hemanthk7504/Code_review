from ..core.schemas import FullResult, ReviewResult, VerificationStatus



ICON = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}


def review_comment(result: ReviewResult, max_items: int = 15) -> str:
    s = result.summary
    out = ["## 🤖 Automated Code Review", "",
           f"**Files analysed:** {s.files_analyzed} · **Overall risk:** {s.overall_risk}/100 · "
           f"**AI analysis:** {'on' if s.llm_used else 'off (static only)'}", "",
           f"| Verified | Uncertain | Rejected (hidden) |", "|---|---|---|",
           f"| {s.verified} | {s.uncertain} | {s.rejected} |", ""]
    shown = [f for f in result.findings if f.verification != VerificationStatus.rejected][:max_items]
    if not shown:
        out.append("No verified issues found. ✅")
    for f in shown:
        tag = "verified" if f.verification == VerificationStatus.verified else "uncertain"
        out += [f"### {ICON.get(f.severity.value, '')} {f.title}",
                f"`{f.file}:{f.line}` · {f.category.value} · priority **{f.priority}** "
                f"(risk {f.risk_score}) · {tag} · sources: {', '.join(f.sources)}",
                "", f.description or "", ""]
        if f.recommendation:
            out += [f"**Suggestion:** {f.recommendation}", ""]
        out += [f"_Verification: {f.verification_reason}_", ""]
    if result.skipped_files:
        out.append(f"_Skipped (not Python): {', '.join(result.skipped_files)}_")
    return "\n".join(out)


def revision_pr_body(full: FullResult, original_pr: int) -> str:
    out = [f"## 🤖 Proposed automated revision for #{original_pr}", "",
           "This pull request was created automatically. The original PR was **not** changed. "
           "Please review the changes before merging.", ""]
    for o in full.revisions:
        v = o.validation
        status = "✅ accepted" if v.accepted else "❌ rejected"
        out += [f"### `{o.revision.path}` — {status}",
                f"- Issues resolved: {v.resolved}/{v.targeted}",
                f"- New issues introduced: {len(v.new_findings)}",
                f"- Risk: {v.risk_before} → {v.risk_after}", ""]
        for c in o.revision.changes:
            out.append(f"- **Problem:** {c.problem}  \n  **Change:** {c.modification}")
        out += ["", "<details><summary>Diff</summary>", "", "```diff", o.revision.diff[:6000], "```", "</details>", ""]
    return "\n".join(out)
