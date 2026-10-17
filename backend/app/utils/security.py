"""API key check and GitHub webhook signature check."""
import hashlib
import hmac
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from ..core.config import get_settings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def require_api_key(
    bearer_token: Optional[str] = Depends(oauth2_scheme),
    x_api_key: Optional[str] = Header(default=None),
) -> None:
    """Accepts either a valid JWT Bearer token OR an X-API-Key header.
    
    Preserves 100% backward compatibility for existing tests, CI/CD runners, and API clients.
    """
    settings = get_settings()

    # 1. If Bearer token provided, validate JWT
    if bearer_token:
        from ..auth import decode_jwt_token, get_user_by_username
        payload = decode_jwt_token(bearer_token)
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token payload.")
        user = get_user_by_username(username)
        if not user or user.disabled:
            raise HTTPException(status_code=401, detail="User account not found or disabled.")
        return

    # 2. If API Key required by server configuration
    if settings.api_key:
        if x_api_key and hmac.compare_digest(x_api_key, settings.api_key):
            return
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing authentication credentials (provide Authorization: Bearer <token> or X-API-Key).",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_github_signature(body: bytes, signature: Optional[str]) -> bool:
    secret = get_settings().github_webhook_secret
    if not secret:
        return True  # signature check disabled
    if not signature or not signature.startswith("sha256="):
        return False
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature.removeprefix("sha256="), digest)
