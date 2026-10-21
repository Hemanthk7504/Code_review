"""Benchmark Evaluator for CodeSentinel Evidence-Based Verification.

Executes the analysis & self-verification pipeline across the held-out labelled
dataset, measuring Precision, Recall, False-Positive Rate (FPR), Accuracy,
F1 Score, Revision Success Rate, and Newly Introduced Defect Rate.
"""
import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ..core.schemas import FileInput, VerificationStatus
from ..engine.analysis import analyze_files
from ..remediation.fixer import generate_revisions
from ..remediation.revalidation import validate_revision
from .dataset import BENCHMARK_DATASET, BenchmarkCase


log = logging.getLogger(__name__)


class BenchmarkMetricBreakdown(BaseModel):
    total_cases: int
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float
    recall: float
    false_positive_rate: float
    accuracy: float
    f1_score: float


class BenchmarkEvaluationResult(BaseModel):
    evaluated_at: str
    total_cases: int
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float
    recall: float
    false_positive_rate: float
    accuracy: float
    f1_score: float
    target_precision_met: bool = Field(description="True if measured precision >= 0.95 (95%)")
    revision_success_rate: float
    newly_introduced_defect_rate: float
    by_language: Dict[str, BenchmarkMetricBreakdown] = Field(default_factory=dict)
    case_results: List[Dict[str, Any]] = Field(default_factory=list)


def _calc_metrics(tp: int, fp: int, tn: int, fn: int) -> tuple[float, float, float, float, float]:
    total = tp + fp + tn + fn
    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 1.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 1.0
    fpr = round(fp / (fp + tn), 4) if (fp + tn) > 0 else 0.0
    acc = round((tp + tn) / total, 4) if total > 0 else 1.0
    f1 = round((2 * precision * recall) / (precision + recall), 4) if (precision + recall) > 0 else 0.0
    return precision, recall, fpr, acc, f1


async def run_benchmark_evaluation(
    dataset: Optional[List[BenchmarkCase]] = None,
    evaluate_remediation: bool = True
) -> BenchmarkEvaluationResult:
    """Run empirical benchmark evaluation on the labelled ground-truth dataset."""
    cases = dataset if dataset is not None else BENCHMARK_DATASET
    tp, fp, tn, fn = 0, 0, 0, 0
    case_results: List[Dict[str, Any]] = []

    # Per-language counters: {lang: [tp, fp, tn, fn]}
    lang_counters: Dict[str, List[int]] = {}

    rev_attempted = 0
    rev_accepted = 0
    rev_with_new_defects = 0

    for case in cases:
        if case.language not in lang_counters:
            lang_counters[case.language] = [0, 0, 0, 0]

        findings, skipped = await analyze_files([FileInput(path=case.filename, content=case.code)])
        verified = [f for f in findings if f.verification == VerificationStatus.verified]
        rejected = [f for f in findings if f.verification == VerificationStatus.rejected]
        uncertain = [f for f in findings if f.verification == VerificationStatus.uncertain]
        flagged = len(verified) > 0

        outcome_status = ""
        if case.is_defect and flagged:
            tp += 1
            lang_counters[case.language][0] += 1
            outcome_status = "TP"
        elif not case.is_defect and flagged:
            fp += 1
            lang_counters[case.language][1] += 1
            outcome_status = "FP"
        elif not case.is_defect and not flagged:
            tn += 1
            lang_counters[case.language][2] += 1
            outcome_status = "TN"
        else:  # case.is_defect and not flagged
            fn += 1
            lang_counters[case.language][3] += 1
            outcome_status = "FN"

        # Evaluate remediation pipeline on real defect cases
        remediation_outcome = None
        if evaluate_remediation and case.is_defect and verified:
            try:
                contents = {case.filename: case.code}
                revs = await generate_revisions(contents, verified, allow_fallback=True)
                if revs:
                    for r in revs:
                        rev_attempted += 1
                        val = await validate_revision(r, findings)
                        if val.accepted:
                            rev_accepted += 1
                        if val.new_findings:
                            rev_with_new_defects += 1
                        remediation_outcome = {
                            "accepted": val.accepted,
                            "resolved": val.resolved,
                            "new_findings": len(val.new_findings),
                            "tests_passed": val.tests_passed,
                        }
            except Exception as rev_err:
                log.warning("Remediation evaluation error for %s: %s", case.id, rev_err)

        case_results.append({
            "id": case.id,
            "language": case.language,
            "filename": case.filename,
            "is_defect": case.is_defect,
            "flagged": flagged,
            "outcome": outcome_status,
            "findings_count": len(findings),
            "verified_count": len(verified),
            "rejected_count": len(rejected),
            "uncertain_count": len(uncertain),
            "remediation": remediation_outcome,
        })

    precision, recall, fpr, accuracy, f1 = _calc_metrics(tp, fp, tn, fn)

    by_language: Dict[str, BenchmarkMetricBreakdown] = {}
    for lang, counts in lang_counters.items():
        l_tp, l_fp, l_tn, l_fn = counts
        lp, lr, lfpr, lacc, lf1 = _calc_metrics(l_tp, l_fp, l_tn, l_fn)
        by_language[lang] = BenchmarkMetricBreakdown(
            total_cases=sum(counts),
            true_positives=l_tp,
            false_positives=l_fp,
            true_negatives=l_tn,
            false_negatives=l_fn,
            precision=lp,
            recall=lr,
            false_positive_rate=lfpr,
            accuracy=lacc,
            f1_score=lf1,
        )

    rev_success_rate = round(rev_accepted / rev_attempted, 4) if rev_attempted > 0 else 1.0
    new_defect_rate = round(rev_with_new_defects / rev_attempted, 4) if rev_attempted > 0 else 0.0

    return BenchmarkEvaluationResult(
        evaluated_at=datetime.now(timezone.utc).isoformat(),
        total_cases=len(cases),
        true_positives=tp,
        false_positives=fp,
        true_negatives=tn,
        false_negatives=fn,
        precision=precision,
        recall=recall,
        false_positive_rate=fpr,
        accuracy=accuracy,
        f1_score=f1,
        target_precision_met=(precision >= 0.95),
        revision_success_rate=rev_success_rate,
        newly_introduced_defect_rate=new_defect_rate,
        by_language=by_language,
        case_results=case_results,
    )


# Cached singleton result
_cached_benchmark_result: Optional[BenchmarkEvaluationResult] = None


async def get_or_run_benchmark(force_refresh: bool = False) -> BenchmarkEvaluationResult:
    """Get the cached benchmark result or run a fresh evaluation."""
    global _cached_benchmark_result
    if _cached_benchmark_result is None or force_refresh:
        _cached_benchmark_result = await run_benchmark_evaluation()
    return _cached_benchmark_result
