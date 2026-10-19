"""Backend root entrypoint proxying to backend.app.main."""
try:
    from backend.app.main import app
except ImportError:
    from app.main import app
# Removed unused import: from main import main


__all__ = ["app"]
