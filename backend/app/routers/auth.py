"""JWT Authentication Endpoints (/api/v1/auth)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..core.auth import (ChangePasswordRequest, LoginRequest, RegisterRequest, Token, User,
                    UserRole, create_access_token, create_refresh_token, create_user,
                    decode_jwt_token, get_current_active_user, get_user_by_username,
                    hash_password, require_role, update_user_password, verify_password, USERS_DB)


router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest):
    """Register a new user account and receive JWT credentials."""
    user = create_user(req)
    access_token, expires_in = create_access_token(user)
    refresh_token = create_refresh_token(user)
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
        user=user,
    )


@router.post("/login", response_model=Token)
async def login(req: LoginRequest):
    """Authenticate with username/password to receive access & refresh JWT tokens."""
    uname = req.username.lower().strip()
    user_db = get_user_by_username(uname)
    if not user_db or not verify_password(req.password, user_db.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user_db.disabled:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    user = User(**user_db.model_dump())
    access_token, expires_in = create_access_token(user)
    refresh_token = create_refresh_token(user)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
        user=user,
    )


@router.post("/refresh", response_model=Token)
async def refresh_access_token(req: RefreshTokenRequest):
    """Exchange a valid refresh token for a newly issued access token."""
    payload = decode_jwt_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type for refresh.")

    username = payload.get("sub")
    user_db = get_user_by_username(username)
    if not user_db or user_db.disabled:
        raise HTTPException(status_code=401, detail="User account inactive or not found.")

    user = User(**user_db.model_dump())
    access_token, expires_in = create_access_token(user)
    # Issue fresh refresh token if close to expiry, or reuse
    refresh_token = create_refresh_token(user)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
        user=user,
    )


@router.get("/me", response_model=User)
async def get_current_user_profile(current_user: User = Depends(get_current_active_user)):
    """Retrieve profile and role information for currently authenticated JWT user."""
    return current_user


@router.get("/users", response_model=list[User], dependencies=[Depends(require_role(UserRole.admin))])
async def list_all_users():
    """List all registered users across the platform (Admin privilege required)."""
    return [User(**u.model_dump()) for u in USERS_DB.values()]


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Change password for authenticated user."""
    user_db = get_user_by_username(current_user.username)
    if not user_db or not verify_password(req.old_password, user_db.hashed_password):
        raise HTTPException(status_code=400, detail="Current password incorrect.")

    new_hash = hash_password(req.new_password)
    user_db.hashed_password = new_hash
    update_user_password(current_user.username, new_hash)
    return {"status": "success", "message": "Password successfully updated."}



@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """Logout session acknowledgment."""
    return {"status": "success", "message": f"Successfully logged out {current_user.username}."}
