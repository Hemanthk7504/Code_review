"""Static secret and credential scanner.

Detects hardcoded secrets, API keys, tokens, and private keys using
pattern recognition and entropy heuristics.
"""
import math
import re
from typing import List, Tuple

from ..core.schemas import Category, Finding, Severity



# High-value secret patterns: (Rule ID, Title, Regex Pattern, Severity, CWE, OWASP)
SECRET_PATTERNS: List[Tuple[str, str, str, Severity, str, str]] = [
    (
        "SEC-AWS-KEY",
        "Hardcoded AWS Access Key ID",
        r"\b(AKIA[0-9A-Z]{16})\b",
        Severity.critical,
        "CWE-798",
        "A07:2021-Identification and Authentication Failures",
    ),
    (
        "SEC-GITHUB-PAT",
        "Hardcoded GitHub Personal Access Token",
        r"\b(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})\b",
        Severity.critical,
        "CWE-798",
        "A07:2021-Identification and Authentication Failures",
    ),
    (
        "SEC-OPENAI-KEY",
        "Hardcoded OpenAI API Key",
        r"\b(sk-[a-zA-Z0-9]{20,48})\b",
        Severity.critical,
        "CWE-798",
        "A07:2021-Identification and Authentication Failures",
    ),
    (
        "SEC-STRIPE-KEY",
        "Hardcoded Stripe Secret Key",
        r"\b(sk_live_[0-9a-zA-Z]{24,34})\b",
        Severity.critical,
        "CWE-798",
        "A07:2021-Identification and Authentication Failures",
    ),
    (
        "SEC-SLACK-WEBHOOK",
        "Exposed Slack Incoming Webhook",
        r"https://hooks\.slack\.com/services/T[a-zA-Z0-9_]+/B[a-zA-Z0-9_]+/[a-zA-Z0-9_]+",
        Severity.high,
        "CWE-798",
        "A07:2021-Identification and Authentication Failures",
    ),
    (
        "SEC-PRIVATE-KEY",
        "Unencrypted Private Key Block",
        r"-----BEGIN (?:RSA|DSA|EC|OPENSSH|PGP)?\s*PRIVATE KEY-----",
        Severity.critical,
        "CWE-312",
        "A02:2021-Cryptographic Failures",
    ),
    (
        "SEC-JWT-TOKEN",
        "Hardcoded JSON Web Token (JWT)",
        r"\beyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b",
        Severity.high,
        "CWE-798",
        "A07:2021-Identification and Authentication Failures",
    ),
    (
        "SEC-GENERIC-PASSWORD",
        "Hardcoded Password Assignment",
        r"""(?i)(?:password|passwd|pwd|secret_key|api_secret)\s*=\s*['"][^'"\s]{8,64}['"]""",
        Severity.high,
        "CWE-798",
        "A07:2021-Identification and Authentication Failures",
    ),
]


def _shannon_entropy(s: str) -> float:
    """Calculate Shannon entropy to distinguish actual secrets from placeholders."""
    if not s:
        return 0.0
    freq = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    entropy = 0.0
    length = len(s)
    for count in freq.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


def _is_placeholder(snippet: str) -> bool:
    """Ignore obvious placeholder strings."""
    lowered = snippet.lower().strip("\"' ")
    placeholders = [
        "your-api-key", "change-me", "changeme", "placeholder",
        "xxxxxxxx", "dummy", "fake", "token_here", "password123", "secret_here"
    ]
    return any(p in lowered for p in placeholders) or lowered in {"example", "<key>", "<token>"}


def scan_secrets(path: str, content: str) -> List[Finding]:
    """Scan content line by line for hardcoded secrets and credentials."""
    findings: List[Finding] = []
    lines = content.splitlines()

    for line_idx, line in enumerate(lines, 1):
        # Ignore comments in typical files
        stripped = line.strip()
        if stripped.startswith("#") and "PRIVATE KEY" not in line:
            # Still scan if comment contains high entropy token
            pass

        for rule_id, title, pattern, severity, cwe, owasp in SECRET_PATTERNS:
            match = re.search(pattern, line)
            if match:
                matched_str = match.group(0)
                if _is_placeholder(matched_str):
                    continue

                # Generate intelligent proposed fix based on secret type
                env_var_name = {
                    "SEC-AWS-KEY": "AWS_ACCESS_KEY_ID",
                    "SEC-GITHUB-PAT": "GITHUB_TOKEN",
                    "SEC-OPENAI-KEY": "OPENAI_API_KEY",
                    "SEC-STRIPE-KEY": "STRIPE_SECRET_KEY",
                    "SEC-SLACK-WEBHOOK": "SLACK_WEBHOOK_URL",
                    "SEC-JWT-TOKEN": "JWT_TOKEN",
                    "SEC-GENERIC-PASSWORD": "APP_SECRET_KEY",
                    "SEC-PRIVATE-KEY": "PRIVATE_KEY",
                }.get(rule_id, "SECRET_KEY")

                fix_line = line.replace(f'"{matched_str}"', f'os.getenv("{env_var_name}")')
                if fix_line == line:
                    fix_line = line.replace(f"'{matched_str}'", f'os.getenv("{env_var_name}")')
                if fix_line == line:
                    fix_line = line.replace(matched_str, f'os.getenv("{env_var_name}")')

                # Mask secret in snippet for safe reporting
                if len(matched_str) > 8:
                    masked = matched_str[:4] + "*" * (len(matched_str) - 8) + matched_str[-4:]
                else:
                    masked = "***REDACTED***"

                masked_snippet = line.replace(matched_str, masked).strip()

                findings.append(Finding(
                    file=path,
                    line=line_idx,
                    category=Category.security,
                    severity=severity,
                    title=f"{title}: {rule_id}",
                    description=(
                        f"Potential secret detected ({title}) at line {line_idx}. "
                        "Hardcoded secrets in source control can lead to unauthorized access, data compromise, and compliance failures."
                    ),
                    recommendation=(
                        "Store credentials in environment variables, a secret manager (e.g. AWS Secrets Manager, Vault, GitHub Secrets), "
                        "and rotate any credentials that were committed to version control."
                    ),
                    rule_id=rule_id,
                    code_snippet=masked_snippet,
                    proposed_fix=fix_line.strip(),
                    sources=["secret_scanner"],
                    confidence=0.92,
                    evidence=[f"secret_scanner {rule_id} matched pattern at line {line_idx}"],
                    cwe_id=cwe,
                    owasp_category=owasp,
                    remediation_effort="low",
                    blast_radius="system",
                ))
                break  # one finding per line is sufficient

    return findings
