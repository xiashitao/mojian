"""User-level long-term memory (MVP: remembered birth info, clearable).

Keyed by `memory_key` — the logged-in user id when available, otherwise an
anonymous client id. Lets a returning user skip re-entering their birth info.
"""
from __future__ import annotations

import json

from ..database import get_db
from .models import BirthInfo


def get_birth_info(memory_key: str | None) -> BirthInfo | None:
    """Return the remembered birth info for this user, if any."""
    if not memory_key:
        return None
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT birth_info_json FROM user_memory WHERE memory_key = ?",
            (memory_key,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    try:
        data = json.loads(row["birth_info_json"])
        return BirthInfo(**data)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def save_birth_info(memory_key: str | None, birth_info: BirthInfo) -> None:
    """Persist the user's birth info (only when it's complete)."""
    if not memory_key or not birth_info.is_complete():
        return
    payload = json.dumps(birth_info.dict(), ensure_ascii=False)
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO user_memory (memory_key, birth_info_json, updated_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(memory_key) DO UPDATE SET
                   birth_info_json = excluded.birth_info_json,
                   updated_at = excluded.updated_at""",
            (memory_key, payload),
        )
        conn.commit()
    finally:
        conn.close()


def clear(memory_key: str | None) -> None:
    """Forget everything remembered for this user."""
    if not memory_key:
        return
    conn = get_db()
    try:
        conn.execute("DELETE FROM user_memory WHERE memory_key = ?", (memory_key,))
        conn.commit()
    finally:
        conn.close()
