"""Backend root entrypoint proxying to backend.app.main."""
try:
    from backend.app.main import app
except ImportError:
    from app.main import app
    from app.main import app

__all__ = ["app"]
