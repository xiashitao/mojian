"""Auth routes: register, login, logout, me."""
from __future__ import annotations

import uuid
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
from ..database import get_db

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


@router.post("/logout")
def logout(response: Response):
    clear_auth_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser = Depends(get_current_user)):
    return UserOut(id=user.id, email=user.email, name=user.name, role=user.role)
