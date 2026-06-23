"""Auth utilities: password hashing, JWT sign/verify, FastAPI dependencies."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import Cookie, Depends, HTTPException, Response, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings
from .database import get_db

Role = Literal["user", "pro", "max", "admin"]

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

COOKIE_NAME = "kairos_token"
COOKIE_MAX_AGE = settings.jwt_expire_days * 86400  # seconds


# ── Password ──────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────

def create_token(user_id: str, role: Role) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expire_days)
    return jwt.encode(
        {"sub": user_id, "role": role, "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def set_auth_cookie(response: Response, token: str) -> None:
    """Write JWT into a httpOnly, Secure, SameSite=Lax cookie."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret,
                          algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or expired token")


def _user_from_payload(payload: dict) -> "CurrentUser":
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid token payload")
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, email, name, role FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="User not found")
    return CurrentUser(id=row["id"], email=row["email"],
                       name=row["name"], role=row["role"])


# ── FastAPI dependencies ───────────────────────────────────────────────────

class CurrentUser:
    def __init__(self, id: str, email: str, name: str, role: Role):
        self.id = id
        self.email = email
        self.name = name
        self.role = role


def get_current_user(
    token: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> CurrentUser:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Not authenticated")
    return _user_from_payload(_decode_token(token))


def get_optional_user(
    token: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> CurrentUser | None:
    if not token:
        return None
    try:
        return _user_from_payload(_decode_token(token))
    except HTTPException:
        return None


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Admin access required")
    return user
