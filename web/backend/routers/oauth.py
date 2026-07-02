"""Google 登录（OAuth 2.0 授权码流程）。

浏览器跳到 /auth/google/login → Google 授权页 → 回调 /auth/google/callback：
用 code 换 token、读 Google 已验证的邮箱 → 复用现有用户表（有则登录、无则
建号，与验证码用户同样无密码）→ 下发同一套 JWT cookie → 合并匿名数据 → 跳回站点。

依赖仅用标准库（urllib）+ jose(签 state)，不引额外包。CSRF 由 state 内的
nonce 与短时 cookie 比对保证。
"""
from __future__ import annotations

import json
import secrets
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt

from ..auth import create_token, hash_password, set_auth_cookie
from ..config import settings
from ..database import get_db
from .auth import migrate_anonymous

router = APIRouter(prefix="/auth/google")

_GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO = "https://openidconnect.googleapis.com/v1/userinfo"
_STATE_COOKIE = "kairos_oauth_state"
_STATE_TTL = 600  # state / nonce 有效期（秒）


def _base_url(request: Request) -> str:
    """站点公网根地址（不含结尾斜杠）。优先用配置，回退到请求推断。"""
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")
    return str(request.base_url).rstrip("/")


def _redirect_uri(request: Request) -> str:
    # 必须与 Google 后台登记的「授权重定向 URI」完全一致。
    return f"{_base_url(request)}/api/auth/google/callback"


@router.get("/login")
def google_login(request: Request, anon_id: str | None = None):
    """跳转到 Google 授权页。把 anon_id 编进签名 state，回调时用于合并匿名数据。"""
    if not (settings.google_client_id and settings.google_client_secret):
        raise HTTPException(status_code=503, detail="Google 登录未配置")

    nonce = secrets.token_urlsafe(16)
    state = jwt.encode(
        {
            "nonce": nonce,
            "anon": anon_id or "",
            "exp": datetime.now(timezone.utc) + timedelta(seconds=_STATE_TTL),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": _redirect_uri(request),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    resp = RedirectResponse(f"{_GOOGLE_AUTH}?{urllib.parse.urlencode(params)}")
    # 短时 nonce cookie，回调时与 state 内的 nonce 比对，防 CSRF。
    resp.set_cookie(
        key=_STATE_COOKIE, value=nonce, max_age=_STATE_TTL,
        httponly=True, secure=settings.cookie_secure, samesite="lax",
    )
    return resp


def _post_form(url: str, data: dict) -> dict:
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def _get_json(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


@router.get("/callback")
def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    """Google 回调：换 token、取邮箱、建/取用户、下发 cookie、跳回站点。"""
    base = _base_url(request)
    if error or not code or not state:
        # 用户取消或参数缺失：跳回首页，不算致命。
        return RedirectResponse(f"{base}/?login=cancelled")

    # 1) 校验 state（签名 + 过期）并取回 nonce/anon_id
    try:
        claims = jwt.decode(state, settings.jwt_secret,
                            algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=400, detail="登录状态失效，请重试")
    nonce_cookie = request.cookies.get(_STATE_COOKIE)
    if not nonce_cookie or nonce_cookie != claims.get("nonce"):
        raise HTTPException(status_code=400, detail="登录状态校验失败，请重试")
    anon_id = claims.get("anon") or None

    # 2) 用授权码换 token
    try:
        tok = _post_form(_GOOGLE_TOKEN, {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": _redirect_uri(request),
            "grant_type": "authorization_code",
        })
        access_token = tok["access_token"]
        # 3) 拿用户信息（openid connect userinfo）
        info = _get_json(_GOOGLE_USERINFO, access_token)
    except Exception:
        raise HTTPException(status_code=502, detail="Google 登录失败，请重试")

    email = (info.get("email") or "").lower()
    if not email or not info.get("email_verified", False):
        raise HTTPException(status_code=400, detail="Google 账号邮箱未验证")
    name = info.get("name") or ""

    # 4) 建/取用户（与验证码登录同一套账号体系）
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id, name, role FROM users WHERE email = ?", (email,)
        ).fetchone()
        if existing:
            user_id, uname, role = existing["id"], existing["name"], existing["role"]
        else:
            user_id, uname, role = str(uuid.uuid4()), name, "user"
            # 第三方登录无密码：塞随机不可用 hash，密码登录永远进不去。
            conn.execute(
                "INSERT INTO users (id, email, password_hash, name) VALUES (?, ?, ?, ?)",
                (user_id, email, hash_password(secrets.token_urlsafe(24)), uname),
            )
            conn.commit()
    finally:
        conn.close()

    migrate_anonymous(anon_id, user_id)

    # 5) 下发登录 cookie，跳回站点首页
    resp = RedirectResponse(f"{base}/?login=ok")
    set_auth_cookie(resp, create_token(user_id, role))
    resp.delete_cookie(_STATE_COOKIE, httponly=True,
                       secure=settings.cookie_secure, samesite="lax")
    return resp
