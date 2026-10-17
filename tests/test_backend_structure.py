"""Tests for backend/ and frontend/ folder separation and architecture."""
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def test_folder_separation_integrity():
    """Verify that backend/ contains only python backend files, and frontend/ contains static & templates."""
    backend_dir = PROJECT_ROOT / "backend"
    frontend_dir = PROJECT_ROOT / "frontend"

    assert backend_dir.exists(), "backend/ directory must exist"
    assert (backend_dir / "app").exists(), "backend/app/ directory must exist"
    assert (backend_dir / "main.py").exists(), "backend/main.py must exist"
    
    # Confirm no HTML templates or static files in backend
    html_in_backend = list(backend_dir.rglob("*.html"))
    assert len(html_in_backend) == 0, f"No HTML templates should exist in backend/, found: {html_in_backend}"

    # Confirm frontend folder structure
    assert frontend_dir.exists(), "frontend/ directory must exist"
    assert (frontend_dir / "templates").exists(), "frontend/templates/ must exist"
    assert (frontend_dir / "static").exists(), "frontend/static/ must exist"

    # Confirm critical templates exist in frontend/templates
    assert (frontend_dir / "templates" / "home.html").exists()
    assert (frontend_dir / "templates" / "login.html").exists()
    assert (frontend_dir / "templates" / "dashboard.html").exists()

    # Confirm static assets exist in frontend/static
    assert (frontend_dir / "static" / "css" / "base.css").exists()
    assert (frontend_dir / "static" / "js" / "app.js").exists()


def test_backend_app_import_and_execution():
    """Verify that backend.main and backend.app.main load cleanly and resolve frontend templates/static."""
    from backend.main import app as backend_root_app
    from backend.app.main import app as backend_module_app
    import backend.app.routers.ui as ui_module

    assert backend_root_app is not None
    assert backend_module_app is not None

    # Check template resolution
    assert ui_module.TEMPLATES_DIR.exists()
    assert "frontend" in str(ui_module.TEMPLATES_DIR)

    client = TestClient(backend_root_app)

    # Check homepage renders from frontend/templates
    r_home = client.get("/")
    assert r_home.status_code == 200
    assert "Autonomous AI Code Review" in r_home.text

    # Check login page renders
    r_login = client.get("/login")
    assert r_login.status_code == 200
    assert "Welcome to CodeSentinel" in r_login.text
    assert "Enter your enterprise credentials" in r_login.text
    assert "demo-pass" not in r_login.text

    # Check static asset resolution from frontend/static
    r_css = client.get("/static/css/base.css")
    assert r_css.status_code == 200
    assert len(r_css.text) > 0
