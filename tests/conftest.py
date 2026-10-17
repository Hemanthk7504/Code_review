"""Global pytest configuration ensuring backend package is at the front of sys.path."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

# Clear any conflicting editable namespace finders from global site-packages
sys.path_hooks = [h for h in sys.path_hooks if "_EditableNamespaceFinder" not in str(h)]
sys.path_importer_cache.clear()

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app  # Preload app package and registered module aliases

import pytest


def _reset_users():
    try:
        from backend.app.db.session import SessionLocal
        from backend.app.models.user import UserModel
        from backend.app.core.auth import USERS_DB, hash_password

        
        with SessionLocal() as db:
            db.query(UserModel).filter(UserModel.username.notin_(["admin", "reviewer", "viewer"])).delete()
            for u in db.query(UserModel).all():
                if u.username == "admin":
                    u.hashed_password = hash_password("Admin@123")
                elif u.username == "reviewer":
                    u.hashed_password = hash_password("Reviewer@123")
                elif u.username == "viewer":
                    u.hashed_password = hash_password("Viewer@123")
            db.commit()

        to_remove = [k for k in list(USERS_DB.keys()) if k not in ("admin", "reviewer", "viewer")]
        for k in to_remove:
            USERS_DB.pop(k, None)
        if "admin" in USERS_DB:
            USERS_DB["admin"].hashed_password = hash_password("Admin@123")
        if "reviewer" in USERS_DB:
            USERS_DB["reviewer"].hashed_password = hash_password("Reviewer@123")
        if "viewer" in USERS_DB:
            USERS_DB["viewer"].hashed_password = hash_password("Viewer@123")
    except Exception:
        pass


@pytest.fixture(autouse=True)
def clean_test_users():
    """Ensure tests run against a clean database state, isolating registered accounts."""
    _reset_users()
    yield
    _reset_users()

