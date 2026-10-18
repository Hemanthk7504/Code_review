"""End-to-end orchestration: review -> verify -> fix -> re-validate -> (GitHub PR)."""
import asyncio
import logging
from collections import Counter
from uuid import uuid4

from .analysis import analyze_files
from ..core.config import get_settings
from ..remediation.fixer import generate_revisions, repair_revision
from ..services.github_client import GitHubClient, changed_lines_from_patch
from .llm import llm_client
from ..utils.report import review_comment, revision_pr_body
from ..remediation.revalidation import validate_revision
from .risk import calculate_posture_grade, extract_top_risks, overall_risk, summarize_cwe_counts
from ..core.schemas import (FileInput, FullResult, ReviewResult, ReviewSummary, RevisionOutcome,
                      VerificationStatus)


log = logging.getLogger(__name__)


def _summary(files_analyzed: int, findings) -> ReviewSummary:
    status = Counter(f.verification for f in findings)
    live = [f for f in findings if f.verification != VerificationStatus.rejected]
    risk_val = overall_risk(findings)
    return ReviewSummary(
        files_analyzed=files_analyzed, total_findings=len(findings),
        verified=status[VerificationStatus.verified], rejected=status[VerificationStatus.rejected],
        uncertain=status[VerificationStatus.uncertain],
        by_severity=dict(Counter(f.severity.value for f in live)),
        by_category=dict(Counter(f.category.value for f in live)),
        overall_risk=risk_val, llm_used=llm_client.enabled,
        posture_grade=calculate_posture_grade(risk_val),
        cwe_counts=summarize_cwe_counts(findings),
        top_risks=extract_top_risks(findings, limit=3))


async def review_files(files: list[FileInput]) -> ReviewResult:
    findings, skipped = await analyze_files(files)
    py_count = len(files) - len(skipped)
    return ReviewResult(summary=_summary(py_count, findings), findings=findings, skipped_files=skipped)


async def review_and_revise(files: list[FileInput]) -> FullResult:
    review = await review_files(files)
    notes: list[str] = []
    contents = {f.path: f.content for f in files}
    verified = [f for f in review.findings if f.verification == VerificationStatus.verified]
    if not verified:
        notes.append("No verified issues, so no revision was generated.")
        return FullResult(review=review, notes=notes)
    if not llm_client.enabled:
        notes.append("LLM is off, so no revised code was generated (static review only).")
        return FullResult(review=review, notes=notes)

    revisions = await generate_revisions(contents, verified)
    if not revisions:
        notes.append("The Fix Generation Agent did not produce any usable revision.")

    s = get_settings()
    outcomes: list[RevisionOutcome] = []
    for r in revisions:
        val = await validate_revision(r, review.findings)
        curr_rev = r
        iteration = 1
        while not val.accepted and iteration < s.max_fix_retries and llm_client.enabled:
            iteration += 1
            file_findings = [f for f in verified if f.file == curr_rev.path]
            repaired = await repair_revision(curr_rev.path, contents[curr_rev.path], curr_rev, file_findings, val.reasons, iteration)
            if not repaired:
                break
            repaired_val = await validate_revision(repaired, review.findings)
            curr_rev = repaired
            val = repaired_val
            if val.accepted:
                notes.append(f"Revision for {curr_rev.path} self-healed on iteration {iteration}.")
                break
        outcomes.append(RevisionOutcome(revision=curr_rev, validation=val))

    rejected = [o.revision.path for o in outcomes if not o.validation.accepted]
    if rejected:
        notes.append(f"Revisions rejected by validation: {', '.join(rejected)}")
    return FullResult(review=review, revisions=outcomes, notes=notes)


async def process_pull_request(repo: str, pr_number: int, token: str | None = None,
                               create_revision_pr: bool = True) -> dict:
    """Used by the GitHub Action / webhook. Reviews a PR and opens a separate revision PR."""
    s = get_settings()
    gh = GitHubClient(token)
    pr = await gh.get_pull(repo, pr_number)
    head_ref, head_sha = pr["head"]["ref"], pr["head"]["sha"]
    if head_ref.startswith(s.bot_branch_prefix):
        return {"skipped": "This PR was created by the review bot."}

    files: list[FileInput] = []
    shas: dict[str, str] = {}
    for item in await gh.list_pull_files(repo, pr_number):
        path = item["filename"]
        if item.get("status") == "removed" or not path.endswith(".py"):
            continue
        content, blob_sha = await gh.get_file(repo, path, head_sha)
        shas[path] = blob_sha
        files.append(FileInput(path=path, content=content,
                               changed_lines=changed_lines_from_patch(item.get("patch"))))

    if not files:
        await gh.comment(repo, pr_number, "## 🤖 Automated Code Review\n\nNo Python files changed.")
        return {"files": 0}

    full = await review_and_revise(files)
    await gh.comment(repo, pr_number, review_comment(full.review))

    contents = {f.path: f.content for f in files}
    verified = [f for f in full.review.findings if f.verification == VerificationStatus.verified]

    accepted = [o for o in full.revisions if o.validation.accepted]

    # If full.revisions didn't produce revisions (e.g. LLM off, or failed to return usable code),
    # dynamically synthesize verified deterministic remediations for all detected bugs & security issues
    if not accepted and create_revision_pr and verified:
        fallback_revs = await generate_revisions(contents, verified, allow_fallback=True)
        for r in fallback_revs:
            val = await validate_revision(r, full.review.findings)
            if val.accepted:
                accepted.append(RevisionOutcome(revision=r, validation=val))
        if accepted:
            full.notes = [n for n in full.notes if not n.startswith("LLM is off")]
            full.notes.append("Applied deterministic AST fixes for verified defects (offline/static mode).")

    result = {"files": len(files), "summary": full.review.summary.model_dump(),
              "revisions_accepted": len(accepted), "revisions_total": len(accepted) if not full.revisions else len(full.revisions),
              "notes": full.notes, "revision_pr": None}

    if create_revision_pr and accepted:
        base_ref = pr.get("base", {}).get("ref", "main")
        branch = f"{s.bot_branch_prefix}pr-{pr_number}-{uuid4().hex[:6]}"
        await gh.create_branch(repo, branch, head_sha)
        for o in accepted:
            file_sha = shas.get(o.revision.path)
            await gh.commit_file(repo, o.revision.path, o.revision.revised_code,
                                 f"AI review: fix security & bug defects in {o.revision.path}", branch,
                                 file_sha)
        body = revision_pr_body(FullResult(review=full.review, revisions=accepted), pr_number)
        title = f"🤖 Automated Security & Bug Fixes for #{pr_number}"
        try:
            new_pr = await gh.create_pull(repo, title, branch, head_ref, body)
        except Exception as err:
            log.warning("Could not target head_ref '%s': %s. Retrying targeting base_ref '%s'", head_ref, err, base_ref)
            new_pr = await gh.create_pull(repo, title, branch, base_ref, body)

        result["revision_pr"] = new_pr.get("html_url")
        await gh.comment(repo, pr_number, f"🤖 A revision PR with verified fixes was opened: {new_pr.get('html_url')}")
    return result
