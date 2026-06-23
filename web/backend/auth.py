"""Auth utilities: password hashing, JWT sign/verify, FastAPI dependency."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings
from .database import get_db

Role = Literal["user", "pro", "max", "admin"]

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
_bearer = HTTPBearer(auto_error=False)


# ── Password ──────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────

def create_token(user_id: str, role: Role) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expire_days)
    return jwt.encode(
        {"sub": user_id, "role": role, "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret,
                          algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or expired token")


# ── FastAPI dependencies ───────────────────────────────────

class CurrentUser:
    def __init__(self, id: str, email: str, name: str, role: Role):
        self.id = id
        self.email = email
        self.name = name
        self.role = role


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Not authenticated")
    payload = _decode_token(creds.credentials)
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


def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser | None:
    """Like get_current_user but returns None instead of raising if no token."""
    if not creds:
        return None
    try:
        return get_current_user(creds)
    except HTTPException:
        return None


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Admin access required")
    return user
