"""Auth utilities: password hashing, JWT sign/verify, FastAPI dependencies."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

import bcrypt
from fastapi import Cookie, Depends, HTTPException, Response, status
from jose import JWTError, jwt

from .config import settings
from .database import get_db

Role = Literal["user", "pro", "max", "admin"]

# 统一登录网关接入：cookie 名可配（默认沿用旧名，接入网关时 .env 设 xsticq_session）。
COOKIE_NAME = settings.cookie_name
COOKIE_MAX_AGE = settings.jwt_expire_days * 86400  # seconds


# ── Password ──────────────────────────────────────────────────────────────
# bcrypt directly (not passlib): avoids the passlib/bcrypt>=4.1 backend bug.
# bcrypt only uses the first 72 bytes, so we truncate explicitly.

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ── JWT ───────────────────────────────────────────────────────────────────

def create_token(user_id: str, role: Role) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expire_days)
    return jwt.encode(
        {"sub": user_id, "role": role, "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def set_auth_cookie(response: Response, token: str) -> None:
    """Write JWT into a httpOnly, Secure, SameSite=Lax cookie.

    接入网关时 settings.cookie_domain 设为 .xsticq.com，令 Cookie 跨子域共享。
    """
    kwargs = dict(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    if settings.cookie_domain:
        kwargs["domain"] = settings.cookie_domain
    response.set_cookie(**kwargs)


def clear_auth_cookie(response: Response) -> None:
    kwargs = dict(
        key=COOKIE_NAME,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    if settings.cookie_domain:
        kwargs["domain"] = settings.cookie_domain
    response.delete_cookie(**kwargs)


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
