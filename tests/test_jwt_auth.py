"""Comprehensive tests for JWT Authentication, RBAC, Dual Auth Fallback, and User Lifecycle."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth import USERS_DB, UserRole, create_access_token, decode_jwt_token, get_user_by_username
from app.config import get_settings
from app.main import app

client = TestClient(app)


def test_login_preseeded_accounts():
    """Verify pre-seeded enterprise accounts (Admin, Reviewer, Viewer) authenticate successfully."""
    # 1. Admin account
    res_admin = client.post("/api/v1/auth/login", json={"username": "admin", "password": "Admin@123"})
    assert res_admin.status_code == 200
    data_admin = res_admin.json()
    assert "access_token" in data_admin
    assert "refresh_token" in data_admin
    assert data_admin["token_type"] == "bearer"
    assert data_admin["user"]["role"] == "admin"
    assert data_admin["user"]["username"] == "admin"

    # 2. Reviewer account
    res_rev = client.post("/api/v1/auth/login", json={"username": "reviewer", "password": "Reviewer@123"})
    assert res_rev.status_code == 200
    data_rev = res_rev.json()
    assert data_rev["user"]["role"] == "reviewer"

    # 3. Viewer account
    res_view = client.post("/api/v1/auth/login", json={"username": "viewer", "password": "Viewer@123"})
    assert res_view.status_code == 200
    data_view = res_view.json()
    assert data_view["user"]["role"] == "viewer"


def test_login_invalid_credentials():
    """Verify unauthorized rejection on invalid password or nonexistent user."""
    # Wrong password
    res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "WrongPassword!"})
    assert res.status_code == 401
    assert "Incorrect username or password" in res.json()["detail"]

    # Unknown user
    res_unknown = client.post("/api/v1/auth/login", json={"username": "ghost_user", "password": "AnyPassword123"})
    assert res_unknown.status_code == 401


def test_register_and_login_lifecycle():
    """Verify user registration, duplicate prevention, and token generation."""
    new_user = {
        "username": "alice_dev",
        "email": "alice@company.internal",
        "full_name": "Alice Developer",
        "password": "SecurePassword@123",
        "role": "reviewer",
    }
    # Successful registration
    res = client.post("/api/v1/auth/register", json=new_user)
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["user"]["username"] == "alice_dev"
    assert data["user"]["role"] == "reviewer"

    # Duplicate username check
    res_dup_uname = client.post("/api/v1/auth/register", json=new_user)
    assert res_dup_uname.status_code == 400
    assert "already registered" in res_dup_uname.json()["detail"]

    # Duplicate email check
    new_user_diff_uname = dict(new_user, username="alice2")
    res_dup_email = client.post("/api/v1/auth/register", json=new_user_diff_uname)
    assert res_dup_email.status_code == 400
    assert "already registered" in res_dup_email.json()["detail"]

    # Login with newly registered credentials
    res_login = client.post("/api/v1/auth/login", json={"username": "alice_dev", "password": "SecurePassword@123"})
    assert res_login.status_code == 200
    assert res_login.json()["user"]["username"] == "alice_dev"


def test_refresh_token_exchange():
    """Verify exchanging a valid refresh token for a newly minted access token."""
    login_res = client.post("/api/v1/auth/login", json={"username": "reviewer", "password": "Reviewer@123"})
    assert login_res.status_code == 200
    refresh_token = login_res.json()["refresh_token"]

    # Exchange refresh token
    refresh_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    refresh_data = refresh_res.json()
    assert "access_token" in refresh_data
    assert refresh_data["user"]["username"] == "reviewer"

    # Invalid refresh token rejection
    bad_res = client.post("/api/v1/auth/refresh", json={"refresh_token": "malformed.jwt.token"})
    assert bad_res.status_code == 401


def test_user_profile_endpoint():
    """Verify /api/v1/auth/me returns current user profile with valid Bearer token."""
    login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "Admin@123"})
    token = login_res.json()["access_token"]

    # Valid token
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["username"] == "admin"
    assert me_data["role"] == "admin"

    # Unauthenticated request
    no_auth_res = client.get("/api/v1/auth/me")
    assert no_auth_res.status_code in (401, 403)

    # Malformed token
    bad_auth_res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer bad-token-xyz"})
    assert bad_auth_res.status_code == 401


def test_rbac_admin_vs_reviewer_permissions():
    """Verify RBAC: Only Admin can access /api/v1/auth/users; Reviewer and Viewer are forbidden."""
    # 1. Admin access
    admin_login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "Admin@123"})
    admin_token = admin_login.json()["access_token"]
    res_admin = client.get("/api/v1/auth/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 200
    users_list = res_admin.json()
    assert isinstance(users_list, list)
    assert any(u["username"] == "admin" for u in users_list)

    # 2. Reviewer access (forbidden)
    rev_login = client.post("/api/v1/auth/login", json={"username": "reviewer", "password": "Reviewer@123"})
    rev_token = rev_login.json()["access_token"]
    res_rev = client.get("/api/v1/auth/users", headers={"Authorization": f"Bearer {rev_token}"})
    assert res_rev.status_code == 403
    assert "Operation not permitted" in res_rev.json()["detail"]

    # 3. Viewer access (forbidden)
    view_login = client.post("/api/v1/auth/login", json={"username": "viewer", "password": "Viewer@123"})
    view_token = view_login.json()["access_token"]
    res_view = client.get("/api/v1/auth/users", headers={"Authorization": f"Bearer {view_token}"})
    assert res_view.status_code == 403


def test_dual_authentication_bearer_and_api_key(monkeypatch):
    """Verify protected endpoints accept either JWT Bearer or X-API-Key, and reject invalid credentials."""
    login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "Admin@123"})
    jwt_token = login_res.json()["access_token"]

    sample_req = {"files": [{"path": "a.py", "content": "x = 1\n"}]}

    # 1. Access with valid JWT Bearer
    res_jwt = client.post(
        "/api/v1/review",
        json=sample_req,
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert res_jwt.status_code == 200

    # 2. Access with invalid JWT Bearer
    res_bad_jwt = client.post(
        "/api/v1/review",
        json=sample_req,
        headers={"Authorization": "Bearer invalid.signature.token"},
    )
    assert res_bad_jwt.status_code == 401

    # 3. Configure strict API Key via settings and test X-API-Key
    monkeypatch.setattr(get_settings(), "api_key", "enterprise-secret-key-999")

    # Valid X-API-Key
    res_key = client.post(
        "/api/v1/review",
        json=sample_req,
        headers={"X-API-Key": "enterprise-secret-key-999"},
    )
    assert res_key.status_code == 200

    # Valid JWT Bearer still works when api_key is configured
    res_jwt_with_key_set = client.post(
        "/api/v1/review",
        json=sample_req,
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert res_jwt_with_key_set.status_code == 200

    # Invalid X-API-Key
    res_bad_key = client.post(
        "/api/v1/review",
        json=sample_req,
        headers={"X-API-Key": "wrong-key"},
    )
    assert res_bad_key.status_code == 401

    # Both missing
    res_missing = client.post("/api/v1/review", json=sample_req)
    assert res_missing.status_code == 401


def test_change_password_and_relogin():
    """Verify user can update password and authenticate with the new password."""
    # Register temporary user
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "bob_tester",
            "email": "bob@enterprise.internal",
            "full_name": "Bob Tester",
            "password": "OldPassword@123",
            "role": "reviewer",
        },
    )
    # Login with old password
    login_res = client.post("/api/v1/auth/login", json={"username": "bob_tester", "password": "OldPassword@123"})
    token = login_res.json()["access_token"]

    # Change password
    change_res = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "OldPassword@123", "new_password": "BrandNewPassword@456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert change_res.status_code == 200

    # Old password no longer works
    fail_res = client.post("/api/v1/auth/login", json={"username": "bob_tester", "password": "OldPassword@123"})
    assert fail_res.status_code == 401

    # New password works
    success_res = client.post("/api/v1/auth/login", json={"username": "bob_tester", "password": "BrandNewPassword@456"})
    assert success_res.status_code == 200


def test_logout_and_ui_login_view():
    """Verify logout endpoint and Jinja2 /login page render."""
    # Test logout endpoint
    login_res = client.post("/api/v1/auth/login", json={"username": "viewer", "password": "Viewer@123"})
    token = login_res.json()["access_token"]
    logout_res = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_res.status_code == 200
    assert "Successfully logged out" in logout_res.json()["message"]

    # Test UI /login page renders cleanly with NO sidebar and NO exposed demo passwords
    ui_res = client.get("/login")
    assert ui_res.status_code == 200
    html = ui_res.text
    assert "Welcome to CodeSentinel" in html
    assert "Sign In to Console" in html
    assert "Admin@123" not in html  # Demo passwords must not be exposed in the UI
    assert "Quick Demo Sign-In" not in html  # Demo pills removed from UI
    assert 'id="app-sidebar"' not in html  # Sidebar must not be present on login page


def test_homepage_is_separate_and_has_no_sidebar():
    """Verify separate public homepage at / with hero section, features, pipeline, and no sidebar."""
    res = client.get("/")
    assert res.status_code == 200
    text = res.text
    assert "Autonomous AI Code Review & Remediation Platform" in text
    assert "The 7-Stage Cognitive Pipeline" in text
    assert "Built for Modern Engineering Organizations" in text
    assert "Launch Console / Sign In" in text
    assert 'id="app-sidebar"' not in text  # Public homepage must not render console sidebar
    assert "window.location.replace('/login')" not in text  # Public homepage is viewable without login


def test_dashboard_auth_guard():
    """Verify that dashboard and protected pages have the strict route guard protecting against unauthenticated viewing."""
    # 1. Dashboard page must contain strict authentication check and redirect
    dash_res = client.get("/dashboard")
    assert dash_res.status_code == 200
    dash_html = dash_res.text
    assert "codesentinel_token" in dash_html
    assert "window.location.replace('/login')" in dash_html
    assert "document.documentElement.style.display = 'none'" in dash_html
    assert 'id="app-sidebar"' in dash_html  # Dashboard has the full console sidebar

    # 2. Login page must NOT contain the redirect back to /login
    login_res = client.get("/login")
    assert login_res.status_code == 200
    login_html = login_res.text
    assert "window.location.replace('/login')" not in login_html

    # 3. Other protected views must also include the route guard and sidebar
    for route in ["/review/new", "/review/results", "/revisions", "/policies"]:
        resp = client.get(route)
        assert resp.status_code == 200
        assert "window.location.replace('/login')" in resp.text
        assert 'id="app-sidebar"' in resp.text


