"""Complete Enterprise JWT Authentication & RBAC (Role-Based Access Control) System."""
import hashlib
import hmac
import os
import time
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field

from .config import get_settings


class UserRole(str, Enum):
    admin = "admin"
    reviewer = "reviewer"
    viewer = "viewer"


class User(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    username: str
    email: str
    full_name: str = ""
    role: UserRole = UserRole.viewer
    disabled: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class UserInDB(User):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User


class TokenPayload(BaseModel):
    sub: str
    role: str
    type: str  # "access" or "refresh"
    exp: int


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str = ""
    role: UserRole = UserRole.reviewer


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


# ---------------- PASSWORD HASHING (PBKDF2-HMAC-SHA256) ----------------

def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """Generate secure salted PBKDF2-HMAC-SHA256 password hash."""
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}:{key.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Safely verify password against stored salted hash with constant-time comparison."""
    try:
        salt_hex, key_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100000)
        return hmac.compare_digest(key.hex(), key_hex)
    except Exception:
        return False


# ---------------- USERS DATABASE & PRE-SEEDED ACCOUNTS ----------------

USERS_DB: dict[str, UserInDB] = {
    "admin": UserInDB(
        id="usr-admin001",
        username="admin",
        email="admin@codesentinel.internal",
        full_name="Enterprise Administrator",
        role=UserRole.admin,
        disabled=False,
        hashed_password=hash_password("Admin@123"),
    ),
    "reviewer": UserInDB(
        id="usr-reviewer002",
        username="reviewer",
        email="reviewer@codesentinel.internal",
        full_name="Staff Security Engineer",
        role=UserRole.reviewer,
        disabled=False,
        hashed_password=hash_password("Reviewer@123"),
    ),
    "viewer": UserInDB(
        id="usr-viewer003",
        username="viewer",
        email="viewer@codesentinel.internal",
        full_name="Compliance Auditor",
        role=UserRole.viewer,
        disabled=False,
        hashed_password=hash_password("Viewer@123"),
    ),
}


def get_user_by_username(username: str) -> Optional[UserInDB]:
    """Retrieve user from cache or persistent SQLite database by username."""
    uname = username.lower().strip()
    if uname in USERS_DB:
        return USERS_DB[uname]

    try:
        from ..db.session import SessionLocal
        from ..models.user import UserModel
        with SessionLocal() as db:
            row = db.query(UserModel).filter_by(username=uname).first()
            if row:
                user_db = UserInDB(
                    id=row.id,
                    username=row.username,
                    email=row.email,
                    full_name=row.full_name or "",
                    role=UserRole(row.role),
                    disabled=row.disabled,
                    hashed_password=row.hashed_password,
                    created_at=row.created_at.isoformat() if hasattr(row.created_at, "isoformat") else str(row.created_at),
                )
                USERS_DB[uname] = user_db
                return user_db
    except Exception:
        pass
    return None


def get_user_by_email(email: str) -> Optional[UserInDB]:
    """Retrieve user from cache or persistent SQLite database by email address."""
    email_clean = email.lower().strip()
    for u in USERS_DB.values():
        if u.email.lower() == email_clean:
            return u

    try:
        from ..db.session import SessionLocal
        from ..models.user import UserModel
        with SessionLocal() as db:
            row = db.query(UserModel).filter_by(email=email_clean).first()
            if row:
                user_db = UserInDB(
                    id=row.id,
                    username=row.username,
                    email=row.email,
                    full_name=row.full_name or "",
                    role=UserRole(row.role),
                    disabled=row.disabled,
                    hashed_password=row.hashed_password,
                    created_at=row.created_at.isoformat() if hasattr(row.created_at, "isoformat") else str(row.created_at),
                )
                USERS_DB[row.username] = user_db
                return user_db
    except Exception:
        pass
    return None


def create_user(req: RegisterRequest) -> User:
    """Create and register a new user in persistent database and active cache."""
    uname = req.username.lower().strip()
    if get_user_by_username(uname):
        raise HTTPException(status_code=400, detail="Username already registered.")
    if get_user_by_email(req.email):
        raise HTTPException(status_code=400, detail="Email already registered.")

    user_db = UserInDB(
        username=uname,
        email=req.email.lower().strip(),
        full_name=req.full_name,
        role=req.role,
        disabled=False,
        hashed_password=hash_password(req.password),
    )
    USERS_DB[uname] = user_db

    # Persist in SQLite
    try:
        from ..db.session import SessionLocal
        from ..models.user import UserModel
        with SessionLocal() as db:
            db_user = UserModel(
                id=user_db.id,
                username=user_db.username,
                email=user_db.email,
                full_name=user_db.full_name,
                role=user_db.role.value,
                disabled=user_db.disabled,
                hashed_password=user_db.hashed_password,
            )
            db.add(db_user)
            db.commit()
    except Exception:
        pass

    return User(**user_db.model_dump())


def update_user_password(username: str, new_hashed_password: str) -> None:
    """Update user password in memory and persistent SQLite database."""
    uname = username.lower().strip()
    if uname in USERS_DB:
        USERS_DB[uname].hashed_password = new_hashed_password

    try:
        from ..db.session import SessionLocal
        from ..models.user import UserModel
        with SessionLocal() as db:
            row = db.query(UserModel).filter_by(username=uname).first()
            if row:
                row.hashed_password = new_hashed_password
                db.commit()
    except Exception:
        pass



# ---------------- JWT CREATION & VALIDATION ----------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def create_access_token(user: User, expires_delta: Optional[timedelta] = None) -> tuple[str, int]:
    """Generate signed JWT access token."""
    s = get_settings()
    expire_minutes = expires_delta.total_seconds() / 60 if expires_delta else s.jwt_access_token_expire_minutes
    exp_timestamp = int(time.time() + expire_minutes * 60)

    payload = {
        "sub": user.username,
        "email": user.email,
        "role": user.role.value,
        "type": "access",
        "exp": exp_timestamp,
        "iat": int(time.time()),
        "jti": uuid4().hex,
    }
    token = jwt.encode(payload, s.jwt_secret_key, algorithm=s.jwt_algorithm)
    return token, int(expire_minutes * 60)


def create_refresh_token(user: User, expires_delta: Optional[timedelta] = None) -> str:
    """Generate signed JWT refresh token."""
    s = get_settings()
    expire_days = expires_delta.days if expires_delta else s.jwt_refresh_token_expire_days
    exp_timestamp = int(time.time() + expire_days * 86400)

    payload = {
        "sub": user.username,
        "type": "refresh",
        "exp": exp_timestamp,
        "iat": int(time.time()),
        "jti": uuid4().hex,
    }
    return jwt.encode(payload, s.jwt_secret_key, algorithm=s.jwt_algorithm)


def decode_jwt_token(token: str) -> dict[str, Any]:
    """Validate signature and decode JWT payload."""
    s = get_settings()
    try:
        return jwt.decode(token, s.jwt_secret_key, algorithms=[s.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------- FASTAPI SECURITY DEPENDENCIES ----------------

async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> User:
    """Authenticate request using Bearer JWT token."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide Authorization: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_jwt_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type for access.")

    username: Optional[str] = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Could not validate credentials.")

    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User account not found.")
    return User(**user.model_dump())


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure authenticated user is active."""
    if current_user.disabled:
        raise HTTPException(status_code=403, detail="Inactive user account.")
    return current_user


def require_role(roles: list[UserRole] | UserRole):
    """RBAC Dependency enforcing minimum role permissions."""
    allowed = [roles] if isinstance(roles, UserRole) else roles

    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        # Admin can access all role-gated routes
        if current_user.role == UserRole.admin or current_user.role in allowed:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operation not permitted. Required role: {[r.value for r in allowed]}; your role: {current_user.role.value}"
        )

    return role_checker


# ---------------- DUAL AUTHENTICATION (JWT BEARER OR X-API-KEY) ----------------

async def require_auth_or_api_key(
    bearer_token: Optional[str] = Depends(oauth2_scheme),
    x_api_key: Optional[str] = Header(default=None),
) -> Optional[User]:
    """Accepts either a valid JWT Bearer token OR an X-API-Key header."""
    s = get_settings()

    # 1. Check JWT Bearer token if supplied
    if bearer_token:
        try:
            payload = decode_jwt_token(bearer_token)
            username = payload.get("sub")
            if username:
                user = get_user_by_username(username)
                if user and not user.disabled:
                    return User(**user.model_dump())
        except Exception:
            pass

    # 2. Check X-API-Key header
    if s.api_key:
        if x_api_key and hmac.compare_digest(x_api_key, s.api_key):
            return User(
                id="service-account",
                username="api_key_service",
                email="system@codesentinel.internal",
                full_name="API Key Service Account",
                role=UserRole.admin,
                disabled=False,
            )
        raise HTTPException(status_code=401, detail="Invalid or missing authentication credentials (JWT Bearer or X-API-Key required).")

    # 3. If api_key is empty (open dev mode), allow with virtual guest
    return User(
        id="guest-dev",
        username="developer",
        email="dev@codesentinel.local",
        full_name="Local Developer",
        role=UserRole.admin,
        disabled=False,
    )
