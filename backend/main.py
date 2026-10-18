"""Backend root entrypoint proxying to backend.app.main."""
from .app.main import app



__all__ = ["app"]
