"""CodeSentinel Enterprise Backend Application Package."""
import sys

# Import packages
from . import core, engine, scanners, remediation, services, utils, models, db, routers

# Re-export key modules directly
from .core import config, schemas, auth
from .engine import pipeline, analysis, agents, llm, consolidation, verifier, risk
from .scanners import static_analysis, secret_scanner, sca
from .remediation import fixer, revalidation
from .services import policy_engine, compliance, dashboard, github_client, jobs
from .utils import cwe_mapping, report, sarif, security

# Register sys.modules aliases for 100% backward compatibility
_aliases = {
    "config": config,
    "schemas": schemas,
    "auth": auth,
    "pipeline": pipeline,
    "analysis": analysis,
    "agents": agents,
    "llm": llm,
    "consolidation": consolidation,
    "verifier": verifier,
    "risk": risk,
    "static_analysis": static_analysis,
    "secret_scanner": secret_scanner,
    "sca": sca,
    "fixer": fixer,
    "revalidation": revalidation,
    "policy_engine": policy_engine,
    "compliance": compliance,
    "dashboard": dashboard,
    "github_client": github_client,
    "jobs": jobs,
    "cwe_mapping": cwe_mapping,
    "report": report,
    "sarif": sarif,
    "security": security,
}

for name, mod in _aliases.items():
    sys.modules[f"app.{name}"] = mod
    sys.modules[f"backend.app.{name}"] = mod

__all__ = [
    "core", "engine", "scanners", "remediation", "services", "utils", "models", "db", "routers",
    *list(_aliases.keys()),
]
