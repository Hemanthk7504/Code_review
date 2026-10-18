"""Backend root entrypoint proxying to backend.app.main."""
from .app.main import app
from main import main


__all__ = ["app"]
