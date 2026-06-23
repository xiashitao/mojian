"""POST /api/auth/register and /api/auth/login."""
from __future__ import annotations

import uuid
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from ..auth import create_token, hash_password, verify_password, get_current_user, CurrentUser
from ..database import get_db
from fastapi import Depends

router = APIRouter(prefix="/auth")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field("", max_length=64)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(req: RegisterRequest):
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (req.email,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Email already registered")
        user_id = str(uuid.uuid4())
        password_hash = hash_password(req.password)
        conn.execute(
            "INSERT INTO users (id, email, password_hash, name) VALUES (?, ?, ?, ?)",
            (user_id, req.email, password_hash, req.name),
        )
        conn.commit()
    finally:
        conn.close()

    token = create_token(user_id, "user")
    return AuthResponse(
        token=token,
        user={"id": user_id, "email": req.email, "name": req.name, "role": "user"},
    )


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest):
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

    token = create_token(row["id"], row["role"])
    return AuthResponse(
        token=token,
        user={"id": row["id"], "email": row["email"],
              "name": row["name"], "role": row["role"]},
    )


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user)):
    return {"id": user.id, "email": user.email,
            "name": user.name, "role": user.role}
