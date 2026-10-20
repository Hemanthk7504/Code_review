"""UI Router serving Jinja2 templates for the CodeSentinel Web Application."""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

def _resolve_templates_dir() -> Path:
    current = Path(__file__).resolve().parent
    candidates = [
        current.parent.parent.parent / "frontend" / "templates",
        current.parent.parent / "frontend" / "templates",
        current.parent.parent / "templates",
        current.parent / "templates",
    ]
    for p in candidates:
        if p.exists() and p.is_dir():
            return p
    return candidates[0]

TEMPLATES_DIR = _resolve_templates_dir()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

ui_router = APIRouter(include_in_schema=False)


@ui_router.get("/", response_class=HTMLResponse)
async def index_view(request: Request):
    return templates.TemplateResponse(request=request, name="home.html", context={"active_page": "home"})


@ui_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_view(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"active_page": "dashboard"})


@ui_router.get("/review/new", response_class=HTMLResponse)
async def new_review_view(request: Request):
    return templates.TemplateResponse(request=request, name="new_review.html", context={"active_page": "new_review"})


@ui_router.get("/review/results", response_class=HTMLResponse)
@ui_router.get("/results", response_class=HTMLResponse)
async def results_view(request: Request):
    return templates.TemplateResponse(request=request, name="results.html", context={"active_page": "results"})


@ui_router.get("/revisions", response_class=HTMLResponse)
async def revisions_view(request: Request):
    return templates.TemplateResponse(request=request, name="revisions.html", context={"active_page": "revisions"})


@ui_router.get("/pull-requests", response_class=HTMLResponse)
async def pull_requests_view(request: Request):
    return templates.TemplateResponse(request=request, name="pull_requests.html", context={"active_page": "pull_requests"})


@ui_router.get("/analytics", response_class=HTMLResponse)
async def analytics_view(request: Request):
    return templates.TemplateResponse(request=request, name="analytics.html", context={"active_page": "analytics"})


@ui_router.get("/repositories", response_class=HTMLResponse)
async def repositories_view(request: Request):
    return templates.TemplateResponse(request=request, name="repositories.html", context={"active_page": "repositories"})


@ui_router.get("/audit-log", response_class=HTMLResponse)
async def audit_log_view(request: Request):
    return templates.TemplateResponse(request=request, name="audit_log.html", context={"active_page": "audit_log"})


@ui_router.get("/team", response_class=HTMLResponse)
async def team_view(request: Request):
    return templates.TemplateResponse(request=request, name="team.html", context={"active_page": "team"})


@ui_router.get("/settings", response_class=HTMLResponse)
async def settings_view(request: Request):
    return templates.TemplateResponse(request=request, name="settings.html", context={"active_page": "settings"})


@ui_router.get("/integrations", response_class=HTMLResponse)
async def integrations_view(request: Request):
    return templates.TemplateResponse(request=request, name="integrations.html", context={"active_page": "integrations"})


@ui_router.get("/policies", response_class=HTMLResponse)
async def policies_view(request: Request):
    return templates.TemplateResponse(request=request, name="policies.html", context={"active_page": "policies"})


@ui_router.get("/compliance", response_class=HTMLResponse)
async def compliance_view(request: Request):
    return templates.TemplateResponse(request=request, name="compliance.html", context={"active_page": "compliance"})


@ui_router.get("/dependencies", response_class=HTMLResponse)
async def dependencies_view(request: Request):
    return templates.TemplateResponse(request=request, name="dependencies.html", context={"active_page": "dependencies"})


@ui_router.get("/login", response_class=HTMLResponse)
async def login_view(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"active_page": "login"})


