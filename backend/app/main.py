import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from contextlib import asynccontextmanager

from .core.config import get_settings

from .db.session import init_db
from .routers.api import router as api_router
from .routers.auth import router as auth_router
from .routers.ui import ui_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

def _resolve_static_dir() -> Path:
    current = Path(__file__).resolve().parent
    candidates = [
        current.parent.parent / "frontend" / "static",
        current.parent / "frontend" / "static",
        current.parent.parent / "static",
        current.parent / "static",
    ]
    for p in candidates:
        if p.exists() and p.is_dir():
            return p
    return candidates[0]

STATIC_DIR = _resolve_static_dir()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database schema is created and default credentials are seeded."""
    try:
        init_db()
    except Exception as e:
        logging.getLogger(__name__).warning("Database initialization on startup warning: %s", e)
    yield

app = FastAPI(
    title=get_settings().app_name,
    description="CodeSentinel · Autonomous AI Code Review & Automated Code Revision Platform.",
    version="2.0.0",
    lifespan=lifespan,
)


# Mount static assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Mount API routes (/api/v1/...)
app.include_router(api_router)
app.include_router(auth_router)

# Mount Web UI routes (/, /dashboard, /review/new, /revisions, etc.)
app.include_router(ui_router)

@app.get("/health")
@app.get("/api/health")
def root_health():
    return {"status": "ok", "app": get_settings().app_name}

