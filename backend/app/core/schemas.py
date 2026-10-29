"""Data models shared by the whole framework."""
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


SEVERITY_WEIGHT = {
    Severity.critical: 1.0,
    Severity.high: 0.8,
    Severity.medium: 0.5,
    Severity.low: 0.25,
    Severity.info: 0.1,
}


class Category(str, Enum):
    bug = "bug"
    security = "security"
    quality = "quality"
    refactor = "refactor"
    style = "style"
    complexity = "complexity"
    performance = "performance"


class VerificationStatus(str, Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"
    uncertain = "uncertain"


STATIC_TOOLS = {"pylint", "bandit", "radon", "ast", "secret_scanner"}


class FileInput(BaseModel):
    path: str
    content: str
    changed_lines: Optional[list[int]] = None  # lines touched by the pull request


class Finding(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:10])
    file: str
    line: int = 1
    end_line: Optional[int] = None
    category: Category
    severity: Severity
    title: str
    description: str = ""
    recommendation: str = ""
    code_snippet: str = ""
    proposed_fix: Optional[str] = None
    rule_id: str = ""
    sources: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    evidence: list[str] = Field(default_factory=list)
    verification: VerificationStatus = VerificationStatus.pending
    verification_reason: str = ""
    verification_confidence: Optional[float] = None
    risk_score: float = 0.0
    priority: str = ""
    cwe_id: str = ""
    owasp_category: str = ""
    remediation_effort: str = ""
    blast_radius: str = ""

    @property
    def static_sources(self) -> list[str]:
        return [s for s in self.sources if s in STATIC_TOOLS or "static" in s.lower() or "scanner" in s.lower() or "analyzer" in s.lower() or "ast" in s.lower()]

    @property
    def ai_sources(self) -> list[str]:
        return [s for s in self.sources if s not in self.static_sources]


class ChangeExplanation(BaseModel):
    finding_id: str
    problem: str
    modification: str


class Revision(BaseModel):
    path: str
    original_code: str
    revised_code: str
    diff: str
    changes: list[ChangeExplanation] = Field(default_factory=list)
    targeted_finding_ids: list[str] = Field(default_factory=list)
    syntax_ok: bool = True
    test_code: Optional[str] = None
    iterations: int = 1


class RevisionValidation(BaseModel):
    path: str
    accepted: bool
    syntax_ok: bool
    targeted: int
    resolved: int
    resolution_ratio: float
    unresolved_finding_ids: list[str] = Field(default_factory=list)
    new_findings: list[Finding] = Field(default_factory=list)
    risk_before: float
    risk_after: float
    reasons: list[str] = Field(default_factory=list)
    tests_executed: bool = False
    tests_passed: bool = True
    test_logs: Optional[str] = None


class ReviewSummary(BaseModel):
    files_analyzed: int
    total_findings: int
    verified: int
    rejected: int
    uncertain: int
    by_severity: dict[str, int]
    by_category: dict[str, int]
    overall_risk: float
    llm_used: bool
    posture_grade: str = "A+"
    cwe_counts: dict[str, int] = Field(default_factory=dict)
    top_risks: list[str] = Field(default_factory=list)


class ReviewResult(BaseModel):
    summary: ReviewSummary
    findings: list[Finding]
    skipped_files: list[str] = Field(default_factory=list)


class RevisionOutcome(BaseModel):
    revision: Revision
    validation: RevisionValidation


class FullResult(BaseModel):
    review: ReviewResult
    revisions: list[RevisionOutcome] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class QuickAuditRequest(BaseModel):
    code: str
    filename: str = "snippet.py"


class SarifExportRequest(BaseModel):
    findings: list[Finding]


# ---------- API request models ----------
class ReviewRequest(BaseModel):
    files: list[FileInput]


class PullRequestRequest(BaseModel):
    repo: str  # "owner/name" or full GitHub URL
    pr_number: Optional[int] = None
    github_token: Optional[str] = None
    create_revision_pr: bool = True


class ValidateRepoRequest(BaseModel):
    repo: str
    github_token: Optional[str] = None


class JobInfo(BaseModel):
    job_id: str
    status: str  # queued | running | done | failed
    detail: str = ""
    result: Optional[dict] = None
    progress: int = 0
    current_stage: str = ""
    logs: list[str] = Field(default_factory=list)


# ---------- Advanced Feature Models ----------
class QualityGatePolicy(BaseModel):
    name: str = "Enterprise Standard Gate"
    max_risk_score: float = 40.0
    block_on_critical: bool = True
    block_on_high: bool = True
    block_on_secrets: bool = True
    max_unresolved_findings: int = 5
    require_syntax_check: bool = True
    min_verification_confidence: float = 0.6


class PolicyRuleEvaluation(BaseModel):
    rule: str
    passed: bool
    message: str
    details: Optional[dict] = None


class PolicyEvaluationResult(BaseModel):
    gate_name: str
    status: str  # PASSED | WARNING | BLOCKED
    passed: bool
    score: float
    violations: list[str] = Field(default_factory=list)
    evaluations: list[PolicyRuleEvaluation] = Field(default_factory=list)


class DependencyFinding(BaseModel):
    package: str
    installed_version: str
    vulnerable_spec: str
    cve_id: str
    severity: Severity
    description: str
    fixed_version: str


class DependencyScanResult(BaseModel):
    manifest_type: str
    total_dependencies: int
    vulnerabilities_count: int
    critical_count: int
    high_count: int
    findings: list[DependencyFinding] = Field(default_factory=list)
    risk_score: float = 0.0


class ComplianceItem(BaseModel):
    id: str
    name: str
    description: str
    status: str  # COMPLIANT | NON_COMPLIANT | PARTIALLY_COMPLIANT
    finding_count: int
    associated_cwes: list[str] = Field(default_factory=list)


class ComplianceScorecardResult(BaseModel):
    framework: str  # OWASP_TOP_10 | SOC_2 | PCI_DSS | SANS_TOP_25
    compliance_score: float  # 0 - 100
    compliant_controls: int
    total_controls: int
    items: list[ComplianceItem] = Field(default_factory=list)


class ComplianceScorecardRequest(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    summary: Optional[dict[str, Any]] = None


class PolicyEvaluationRequest(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    summary: Optional[dict[str, Any]] = None
    overall_risk: Optional[float] = None
    gate_name: Optional[str] = None



class IntegrationType(str, Enum):
    slack = "slack"
    teams = "teams"
    discord = "discord"
    jira = "jira"
    linear = "linear"
    datadog = "datadog"
    webhook = "webhook"


class IntegrationConfig(BaseModel):
    id: str
    name: str
    type: IntegrationType
    enabled: bool = True
    target_url: str = ""
    auth_token: Optional[str] = None
    channel_or_project: Optional[str] = None
    events: list[str] = Field(default_factory=lambda: ["review.completed", "finding.critical", "revision.accepted"])


class IntegrationTestRequest(BaseModel):
    integration_type: IntegrationType
    target_url: Optional[str] = None
    auth_token: Optional[str] = None
    channel_or_project: Optional[str] = None


class DependencyScanRequest(BaseModel):
    content: str
    manifest_type: str = "requirements.txt"  # requirements.txt | pyproject.toml | pipfile


class GitHubIssueRequest(BaseModel):
    repo: str
    title: str
    body: str
    labels: Optional[list[str]] = None
    github_token: Optional[str] = None

