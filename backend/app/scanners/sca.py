"""Software Composition Analysis (SCA) & CycloneDX SBOM Generator."""
import re
from typing import Any
from uuid import uuid4

from ..core.schemas import DependencyFinding, DependencyScanResult, Severity


# Known Python vulnerability vulnerability advisory database (CVEs)
KNOWN_VULNERABILITIES = [
    {
        "package": "requests",
        "bad_versions": lambda v: _version_lt(v, "2.31.0"),
        "cve_id": "CVE-2023-32681",
        "severity": Severity.high,
        "description": "Proxy-Authorization header leakage on cross-origin redirects.",
        "fixed_version": "2.31.0",
        "vulnerable_spec": "< 2.31.0",
    },
    {
        "package": "cryptography",
        "bad_versions": lambda v: _version_lt(v, "41.0.0"),
        "cve_id": "CVE-2023-38325",
        "severity": Severity.critical,
        "description": "NULL pointer dereference in certificate revocation list parsing.",
        "fixed_version": "41.0.0",
        "vulnerable_spec": "< 41.0.0",
    },
    {
        "package": "urllib3",
        "bad_versions": lambda v: _version_lt(v, "1.26.17"),
        "cve_id": "CVE-2023-43804",
        "severity": Severity.high,
        "description": "Cookie header not stripped during cross-origin redirect.",
        "fixed_version": "1.26.17",
        "vulnerable_spec": "< 1.26.17",
    },
    {
        "package": "django",
        "bad_versions": lambda v: _version_lt(v, "4.2.4"),
        "cve_id": "CVE-2023-36053",
        "severity": Severity.high,
        "description": "Denial-of-service via catastrophic backtracking in EmailValidator regex.",
        "fixed_version": "4.2.4",
        "vulnerable_spec": "< 4.2.4",
    },
    {
        "package": "flask",
        "bad_versions": lambda v: _version_lt(v, "2.2.5"),
        "cve_id": "CVE-2023-30861",
        "severity": Severity.medium,
        "description": "Session cookie disclosure under misconfigured reverse proxy headers.",
        "fixed_version": "2.2.5",
        "vulnerable_spec": "< 2.2.5",
    },
    {
        "package": "pyyaml",
        "bad_versions": lambda v: _version_lt(v, "5.4"),
        "cve_id": "CVE-2020-14343",
        "severity": Severity.critical,
        "description": "Arbitrary code execution via full-loader deserialization.",
        "fixed_version": "5.4",
        "vulnerable_spec": "< 5.4",
    },
    {
        "package": "pillow",
        "bad_versions": lambda v: _version_lt(v, "10.0.1"),
        "cve_id": "CVE-2023-44271",
        "severity": Severity.high,
        "description": "Uncontrolled memory consumption in image decompression.",
        "fixed_version": "10.0.1",
        "vulnerable_spec": "< 10.0.1",
    },
    {
        "package": "jinja2",
        "bad_versions": lambda v: _version_lt(v, "3.1.3"),
        "cve_id": "CVE-2024-22195",
        "severity": Severity.medium,
        "description": "Cross-site scripting (XSS) via unescaped keys in xmlattr filter.",
        "fixed_version": "3.1.3",
        "vulnerable_spec": "< 3.1.3",
    },
    {
        "package": "aiohttp",
        "bad_versions": lambda v: _version_lt(v, "3.8.6"),
        "cve_id": "CVE-2023-49081",
        "severity": Severity.high,
        "description": "HTTP request smuggling via improper newline parsing.",
        "fixed_version": "3.8.6",
        "vulnerable_spec": "< 3.8.6",
    },
    {
        "package": "paramiko",
        "bad_versions": lambda v: _version_lt(v, "3.4.0"),
        "cve_id": "CVE-2023-48795",
        "severity": Severity.high,
        "description": "Terrapin attack vulnerability allowing SSH sequence number manipulation.",
        "fixed_version": "3.4.0",
        "vulnerable_spec": "< 3.4.0",
    },
]


def _version_lt(v1: str, v2: str) -> bool:
    """Simple semver comparison for dependencies."""
    def parse_parts(v: str):
        parts = re.findall(r"\d+", v)
        return [int(p) for p in parts] or [0]

    p1, p2 = parse_parts(v1), parse_parts(v2)
    max_len = max(len(p1), len(p2))
    p1 += [0] * (max_len - len(p1))
    p2 += [0] * (max_len - len(p2))
    return p1 < p2


def parse_requirements(text: str) -> list[tuple[str, str]]:
    """Extract package name and version from requirements.txt content."""
    dependencies: list[tuple[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # matches: package==1.2.3, package>=1.2.3, package~=1.2.3
        match = re.match(r"^([a-zA-Z0-9_\-\.]+)\s*(?:==|>=|<=|~=)\s*([0-9\.\w]+)", line)
        if match:
            pkg, ver = match.group(1).lower().replace("_", "-"), match.group(2)
            dependencies.append((pkg, ver))
        else:
            # bare package name without version
            match_bare = re.match(r"^([a-zA-Z0-9_\-\.]+)", line)
            if match_bare:
                dependencies.append((match_bare.group(1).lower().replace("_", "-"), "0.0.0"))
    return dependencies


def scan_dependencies(manifest_content: str, manifest_type: str = "requirements.txt") -> DependencyScanResult:
    """Analyze dependency manifest and identify vulnerable packages."""
    deps = parse_requirements(manifest_content)
    findings: list[DependencyFinding] = []

    for pkg, ver in deps:
        for adv in KNOWN_VULNERABILITIES:
            if adv["package"] == pkg:
                if adv["bad_versions"](ver):
                    findings.append(DependencyFinding(
                        package=pkg,
                        installed_version=ver,
                        vulnerable_spec=adv["vulnerable_spec"],
                        cve_id=adv["cve_id"],
                        severity=adv["severity"],
                        description=adv["description"],
                        fixed_version=adv["fixed_version"],
                    ))

    crit_count = sum(1 for f in findings if f.severity == Severity.critical)
    high_count = sum(1 for f in findings if f.severity == Severity.high)

    # Risk score based on CVE counts
    risk = min(100.0, crit_count * 35.0 + high_count * 20.0 + len(findings) * 5.0)

    return DependencyScanResult(
        manifest_type=manifest_type,
        total_dependencies=len(deps),
        vulnerabilities_count=len(findings),
        critical_count=crit_count,
        high_count=high_count,
        findings=findings,
        risk_score=round(risk, 1),
    )


def generate_cyclonedx_sbom(manifest_content: str, app_name: str = "Project") -> dict[str, Any]:
    """Generate an OASIS / OWASP CycloneDX v1.5 JSON Software Bill of Materials (SBOM)."""
    deps = parse_requirements(manifest_content)
    components = []

    for pkg, ver in deps:
        components.append({
            "type": "library",
            "name": pkg,
            "version": ver if ver != "0.0.0" else "latest",
            "purl": f"pkg:pypi/{pkg}@{ver}",
            "scope": "required",
            "licenses": [{"license": {"id": "MIT"}}],
        })

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": "2026-10-17T00:00:00Z",
            "tools": [{"vendor": "CodeSentinel", "name": "SCA-Scanner", "version": "2.0.0"}],
            "component": {
                "name": app_name,
                "type": "application",
                "version": "1.0.0"
            }
        },
        "components": components,
    }
