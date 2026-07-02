"""Auth routes: register, login, logout, me."""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field

from ..auth import (
    CurrentUser,
    clear_auth_cookie,
    create_token,
    get_current_user,
    hash_password,
    set_auth_cookie,
    verify_password,
)
from ..config import settings
from ..database import get_db
from ..services.email import send_login_code

router = APIRouter(prefix="/auth")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field("", max_length=64)
    anon_id: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    anon_id: str | None = None


def migrate_anonymous(anon_id: str | None, user_id: str) -> None:
    """Re-key an anonymous visitor's conversations + memory onto their account."""
    if not anon_id or anon_id == user_id:
        return
    conn = get_db()
    try:
        conn.execute(
            "UPDATE conversations SET user_id = ? WHERE user_id = ?", (user_id, anon_id)
        )
        conn.execute(
            "UPDATE user_memory_notes SET memory_key = ? WHERE memory_key = ?",
            (user_id, anon_id),
        )
        # Birth info: keep the account's own if present, else adopt the anon's.
        has_own = conn.execute(
            "SELECT 1 FROM user_memory WHERE memory_key = ?", (user_id,)
        ).fetchone()
        if has_own:
            conn.execute("DELETE FROM user_memory WHERE memory_key = ?", (anon_id,))
        else:
            conn.execute(
                "UPDATE user_memory SET memory_key = ? WHERE memory_key = ?",
                (user_id, anon_id),
            )
        conn.commit()
    finally:
        conn.close()


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str


@router.post("/register", response_model=UserOut, status_code=201)
def register(req: RegisterRequest, response: Response):
    conn = get_db()
    try:
        if conn.execute("SELECT id FROM users WHERE email = ?", (req.email,)).fetchone():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Email already registered")
        user_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO users (id, email, password_hash, name) VALUES (?, ?, ?, ?)",
            (user_id, req.email, hash_password(req.password), req.name),
        )
        conn.commit()
    finally:
        conn.close()

    migrate_anonymous(req.anon_id, user_id)
    set_auth_cookie(response, create_token(user_id, "user"))
    return UserOut(id=user_id, email=req.email, name=req.name, role="user")


@router.post("/login", response_model=UserOut)
def login(req: LoginRequest, response: Response):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, email, name, role, password_hash FROM users WHERE email = ?",
            (req.email,),
        ).fetchone()
    finally:
        conn.close()

    if not row or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect email or password")

    migrate_anonymous(req.anon_id, row["id"])
    set_auth_cookie(response, create_token(row["id"], row["role"]))
    return UserOut(id=row["id"], email=row["email"],
                   name=row["name"], role=row["role"])


# ── 邮箱验证码登录（OTP，免密码）──────────────────────────────────────────────
class SendCodeRequest(BaseModel):
    email: EmailStr


class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=4, max_length=8)
    anon_id: str | None = None


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


@router.post("/email/send-code")
def send_email_code(req: SendCodeRequest):
    """生成 6 位验证码、存库、发送。同一邮箱有重发冷却，防刷。"""
    email = req.email.lower()
    now = datetime.now(timezone.utc)
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT sent_at FROM email_codes WHERE email = ?", (email,)
        ).fetchone()
        if row:
            sent_at = _parse_dt(row["sent_at"])
            if sent_at and (now - sent_at).total_seconds() < settings.otp_resend_seconds:
                raise HTTPException(status_code=429, detail="发送太频繁，请稍后再试")
        code = f"{secrets.randbelow(1_000_000):06d}"
        expires = now + timedelta(seconds=settings.otp_ttl_seconds)
        conn.execute(
            """INSERT INTO email_codes (email, code, expires_at, attempts, sent_at)
               VALUES (?, ?, ?, 0, ?)
               ON CONFLICT(email) DO UPDATE SET
                 code=excluded.code, expires_at=excluded.expires_at,
                 attempts=0, sent_at=excluded.sent_at""",
            (email, code, expires.isoformat(), now.isoformat()),
        )
        conn.commit()
    finally:
        conn.close()

    try:
        send_login_code(email, code)
    except Exception:
        raise HTTPException(status_code=502, detail="验证码发送失败，请稍后再试")
    return {"ok": True, "resend_after": settings.otp_resend_seconds}


@router.post("/email/verify", response_model=UserOut)
def verify_email_code(req: VerifyCodeRequest, response: Response):
    """校验验证码；通过则建/取用户并下发登录 cookie。"""
    email = req.email.lower()
    now = datetime.now(timezone.utc)
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT code, expires_at, attempts FROM email_codes WHERE email = ?", (email,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="请先获取验证码")
        expires = _parse_dt(row["expires_at"])
        if not expires or now > expires:
            conn.execute("DELETE FROM email_codes WHERE email = ?", (email,))
            conn.commit()
            raise HTTPException(status_code=400, detail="验证码已过期，请重新获取")
        if row["attempts"] >= settings.otp_max_attempts:
            conn.execute("DELETE FROM email_codes WHERE email = ?", (email,))
            conn.commit()
            raise HTTPException(status_code=429, detail="尝试次数过多，请重新获取验证码")
        if req.code.strip() != row["code"]:
            conn.execute(
                "UPDATE email_codes SET attempts = attempts + 1 WHERE email = ?", (email,)
            )
            conn.commit()
            raise HTTPException(status_code=400, detail="验证码不正确")

        # 通过：作废验证码，建或取用户。
        conn.execute("DELETE FROM email_codes WHERE email = ?", (email,))
        existing = conn.execute(
            "SELECT id, name, role FROM users WHERE email = ?", (email,)
        ).fetchone()
        if existing:
            user_id, name, role = existing["id"], existing["name"], existing["role"]
        else:
            user_id, name, role = str(uuid.uuid4()), "", "user"
            # OTP 用户无密码：塞一个随机不可用 hash，密码登录永远进不去。
            conn.execute(
                "INSERT INTO users (id, email, password_hash, name) VALUES (?, ?, ?, ?)",
                (user_id, email, hash_password(secrets.token_urlsafe(24)), name),
            )
        conn.commit()
    finally:
        conn.close()

    migrate_anonymous(req.anon_id, user_id)
    set_auth_cookie(response, create_token(user_id, role))
    return UserOut(id=user_id, email=email, name=name, role=role)


@router.get("/providers")
def providers():
    """前端据此决定显示哪些登录方式（Google 未配置时不显示按钮）。"""
    return {"google": bool(settings.google_client_id and settings.google_client_secret)}


@router.post("/logout")
def logout(response: Response):
    clear_auth_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser = Depends(get_current_user)):
    return UserOut(id=user.id, email=user.email, name=user.name, role=user.role)
