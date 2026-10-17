"""Core package: Configuration, Authentication, and Data Schemas."""
from .config import Settings, get_settings
from .auth import (
    User, UserInDB, UserRole, Token, TokenPayload,
    LoginRequest, RegisterRequest, ChangePasswordRequest,
    hash_password, verify_password, get_user_by_username,
    get_user_by_email, create_user, update_user_password,
    create_access_token, create_refresh_token, decode_jwt_token,
    get_current_user, get_current_active_user, require_role,
    require_auth_or_api_key, USERS_DB, oauth2_scheme
)
from .schemas import (
    Category, Finding, Severity, SEVERITY_WEIGHT,
    FileInput, ReviewResult, FullResult, ReviewSummary,
    Revision, RevisionOutcome, RevisionValidation, VerificationStatus,
    JobInfo, PullRequestRequest, QualityGatePolicy, PolicyEvaluationRequest,
    PolicyEvaluationResult, PolicyRuleEvaluation, SarifExportRequest,
    QuickAuditRequest, IntegrationConfig, IntegrationTestRequest,
    DependencyFinding, DependencyScanRequest, DependencyScanResult,
    ComplianceItem, ComplianceScorecardRequest, ComplianceScorecardResult,
    STATIC_TOOLS
)

__all__ = [
    "Settings", "get_settings",
    "User", "UserInDB", "UserRole", "Token", "TokenPayload",
    "LoginRequest", "RegisterRequest", "ChangePasswordRequest",
    "hash_password", "verify_password", "get_user_by_username",
    "get_user_by_email", "create_user", "update_user_password",
    "create_access_token", "create_refresh_token", "decode_jwt_token",
    "get_current_user", "get_current_active_user", "require_role",
    "require_auth_or_api_key", "USERS_DB", "oauth2_scheme",
    "Category", "Finding", "Severity", "SEVERITY_WEIGHT",
    "FileInput", "ReviewResult", "FullResult", "ReviewSummary",
    "Revision", "RevisionOutcome", "RevisionValidation", "VerificationStatus",
    "JobInfo", "PullRequestRequest", "QualityGatePolicy", "PolicyEvaluationRequest",
    "PolicyEvaluationResult", "PolicyRuleEvaluation", "SarifExportRequest",
    "QuickAuditRequest", "IntegrationConfig", "IntegrationTestRequest",
    "DependencyFinding", "DependencyScanRequest", "DependencyScanResult",
    "ComplianceItem", "ComplianceScorecardRequest", "ComplianceScorecardResult",
    "STATIC_TOOLS",
]
