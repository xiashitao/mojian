"""User-level long-term memory, keyed by (memory_key, subject).

A single user may consult about multiple people — themselves, a spouse,
a child, etc. Each subject has its OWN birth info, consultation notes, and
profile, so they never pollute each other. `subject` defaults to "self"
(kept backward-compatible via DEFAULT_SUBJECT so callers that don't pass it
operate on the user themself, matching pre-multi-subject behaviour).
"""
from __future__ import annotations

import json
import uuid

from ..database import get_db
from .models import BirthInfo, Subject, UserProfile

DEFAULT_SUBJECT: Subject = "self"


def get_birth_info(
    memory_key: str | None,
    subject: Subject = DEFAULT_SUBJECT,
) -> BirthInfo | None:
    """Return the remembered birth info for (user, subject), if any."""
    if not memory_key:
        return None
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT birth_info_json FROM user_memory "
            "WHERE memory_key = ? AND subject = ?",
            (memory_key, subject),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    try:
        data = json.loads(row["birth_info_json"])
        data["subject"] = subject  # keep the row's subject authoritative
        return BirthInfo(**data)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def save_birth_info(
    memory_key: str | None,
    birth_info: BirthInfo,
    subject: Subject = DEFAULT_SUBJECT,
) -> None:
    """Persist the birth info for (user, subject). Only stores when complete."""
    if not memory_key or not birth_info.is_complete():
        return
    payload = json.dumps(birth_info.model_dump(), ensure_ascii=False)
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO user_memory (memory_key, subject, birth_info_json, updated_at)
               VALUES (?, ?, ?, datetime('now'))
               ON CONFLICT(memory_key, subject) DO UPDATE SET
                   birth_info_json = excluded.birth_info_json,
                   updated_at = excluded.updated_at""",
            (memory_key, subject, payload),
        )
        conn.commit()
    finally:
        conn.close()


def add_note(
    memory_key: str | None,
    *,
    topic: str | None,
    question: str,
    conclusion: str,
    analysis_id: str | None = None,
    subject: Subject = DEFAULT_SUBJECT,
) -> None:
    """Append a one-line record of a past consultation for (user, subject)."""
    if not memory_key or not conclusion.strip():
        return
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO user_memory_notes
                   (id, memory_key, subject, topic, question, conclusion, analysis_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (uuid.uuid4().hex, memory_key, subject, topic, question[:200],
             conclusion.strip()[:300], analysis_id),
        )
        conn.commit()
    finally:
        conn.close()


def recent_notes(
    memory_key: str | None,
    subject: Subject = DEFAULT_SUBJECT,
    limit: int = 5,
) -> list[dict]:
    """Most recent consultation notes for (user, subject) (newest first)."""
    if not memory_key:
        return []
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT topic, question, conclusion, analysis_id, created_at
               FROM user_memory_notes
               WHERE memory_key = ? AND subject = ?
               ORDER BY created_at DESC, rowid DESC
               LIMIT ?""",
            (memory_key, subject, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def clear(
    memory_key: str | None,
    subject: Subject | None = None,
) -> None:
    """Forget remembered data for this user.

    subject=None clears ALL subjects (birth info + notes + profile across everyone);
    a specific subject clears only that one.
    """
    if not memory_key:
        return
    conn = get_db()
    try:
        if subject is None:
            conn.execute("DELETE FROM user_memory WHERE memory_key = ?", (memory_key,))
            conn.execute("DELETE FROM user_memory_notes WHERE memory_key = ?", (memory_key,))
            conn.execute("DELETE FROM user_profile WHERE memory_key = ?", (memory_key,))
        else:
            conn.execute(
                "DELETE FROM user_memory WHERE memory_key = ? AND subject = ?",
                (memory_key, subject),
            )
            conn.execute(
                "DELETE FROM user_memory_notes WHERE memory_key = ? AND subject = ?",
                (memory_key, subject),
            )
            conn.execute(
                "DELETE FROM user_profile WHERE memory_key = ? AND subject = ?",
                (memory_key, subject),
            )
        conn.commit()
    finally:
        conn.close()


def list_subjects(memory_key: str | None) -> list[str]:
    """All subjects this user has data for (union across memory/notes/profile).

    Used by the frontend to show a subject switcher. Always includes 'self'
    first if present, then others alphabetically.
    """
    if not memory_key:
        return []
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT DISTINCT subject FROM user_memory WHERE memory_key = ?
               UNION
               SELECT DISTINCT subject FROM user_memory_notes WHERE memory_key = ?
               UNION
               SELECT DISTINCT subject FROM user_profile WHERE memory_key = ?""",
            (memory_key, memory_key, memory_key),
        ).fetchall()
    finally:
        conn.close()
    subjects = sorted({r["subject"] for r in rows if r["subject"]})
    # 'self' first if present (the default/primary subject)
    if "self" in subjects:
        subjects.remove("self")
        subjects = ["self"] + subjects
    return subjects


# ── 用户画像 ────────────────────────────────────────────────────────────────
# 与 birth_info 平行:birth_info 记「这个人的八字」,profile 记「这个人是谁」。
# 按 (memory_key, subject) 隔离 —— 用户本人的画像不会污染配偶/子女的画像。
# core_concerns / traits 是 list,数据库里以 JSON 字符串存储。


def _profile_from_row(row) -> UserProfile | None:
    """Decode a DB row into a UserProfile (parses JSON list fields)."""
    if not row:
        return None
    try:
        core_concerns = json.loads(row["core_concerns"]) if row["core_concerns"] else []
    except (json.JSONDecodeError, TypeError):
        core_concerns = []
    try:
        traits = json.loads(row["traits"]) if row["traits"] else []
    except (json.JSONDecodeError, TypeError):
        traits = []
    return UserProfile(
        life_stage=row["life_stage"] or None,
        core_concerns=core_concerns,
        traits=traits,
        long_term_goal=row["long_term_goal"] or None,
        comm_style=row["comm_style"] or None,
        raw_summary=row["raw_summary"] or None,
    )


def get_profile(
    memory_key: str | None,
    subject: Subject = DEFAULT_SUBJECT,
) -> UserProfile | None:
    """Return the remembered profile for (user, subject), if any."""
    if not memory_key:
        return None
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT life_stage, core_concerns, traits, long_term_goal, "
            "comm_style, raw_summary FROM user_profile "
            "WHERE memory_key = ? AND subject = ?",
            (memory_key, subject),
        ).fetchone()
    finally:
        conn.close()
    return _profile_from_row(row)


def save_profile(
    memory_key: str | None,
    profile: UserProfile,
    subject: Subject = DEFAULT_SUBJECT,
) -> None:
    """Upsert the profile for (user, subject)."""
    if not memory_key:
        return
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO user_profile
                   (memory_key, subject, life_stage, core_concerns, traits, long_term_goal,
                    comm_style, raw_summary, turns_since_update, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, datetime('now'))
               ON CONFLICT(memory_key, subject) DO UPDATE SET
                   life_stage     = excluded.life_stage,
                   core_concerns  = excluded.core_concerns,
                   traits         = excluded.traits,
                   long_term_goal = excluded.long_term_goal,
                   comm_style     = excluded.comm_style,
                   raw_summary    = excluded.raw_summary,
                   turns_since_update = 0,
                   updated_at     = excluded.updated_at""",
            (
                memory_key,
                subject,
                profile.life_stage,
                json.dumps(profile.core_concerns, ensure_ascii=False),
                json.dumps(profile.traits, ensure_ascii=False),
                profile.long_term_goal,
                profile.comm_style,
                profile.raw_summary,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def increment_profile_turns(
    memory_key: str | None,
    subject: Subject = DEFAULT_SUBJECT,
) -> int:
    """+1 the turns counter for (user, subject); return the new value.

    Auto-creates an empty profile row if none exists yet, so the counter has
    somewhere to live from turn one (otherwise first-time users would never
    reach the threshold and never get a profile). The empty row gets filled in
    by save_profile when the LLM update actually runs.
    """
    if not memory_key:
        return 0
    conn = get_db()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO user_profile (memory_key, subject, turns_since_update) "
            "VALUES (?, ?, 0)",
            (memory_key, subject),
        )
        conn.execute(
            "UPDATE user_profile SET turns_since_update = turns_since_update + 1 "
            "WHERE memory_key = ? AND subject = ?",
            (memory_key, subject),
        )
        row = conn.execute(
            "SELECT turns_since_update FROM user_profile "
            "WHERE memory_key = ? AND subject = ?",
            (memory_key, subject),
        ).fetchone()
        conn.commit()
        return int(row["turns_since_update"]) if row else 0
    finally:
        conn.close()
