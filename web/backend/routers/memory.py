"""User memory endpoints — view / clear remembered birth info, per subject."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from ..agent import memory
from ..agent.models import Subject
from ..auth import CurrentUser, get_optional_user

router = APIRouter()


class MemoryRequest(BaseModel):
    anon_id: Optional[str] = None
    # 主体(self/spouse/child/parent/other)。None=默认 self(用户本人)。
    subject: Optional[Subject] = None


def _memory_key(user: CurrentUser | None, anon_id: str | None) -> str | None:
    return (user.id if user else None) or anon_id


@router.post("/memory/birth-info")
def get_remembered_memory(
    req: MemoryRequest,
    user: CurrentUser | None = Depends(get_optional_user),
):
    """Return what we remember about this user for a given subject:
    birth info + recent notes. Defaults to the user themself (subject=self)."""
    key = _memory_key(user, req.anon_id)
    subject = req.subject or "self"
    info = memory.get_birth_info(key, subject)
    return {
        "subject": subject,
        "birth_info": info.model_dump() if info else None,
        "notes": memory.recent_notes(key, subject),
    }


@router.post("/memory/subjects")
def list_subjects(
    req: MemoryRequest,
    user: CurrentUser | None = Depends(get_optional_user),
):
    """List all subjects this user has data for (for the frontend switcher).
    Always includes 'self' first if present."""
    key = _memory_key(user, req.anon_id)
    return {"subjects": memory.list_subjects(key)}


@router.post("/memory/forget")
def forget(
    req: MemoryRequest,
    user: CurrentUser | None = Depends(get_optional_user),
):
    """Clear remembered data. subject=None clears ALL subjects; a specific
    subject clears only that one (e.g. forget just the child's chart)."""
    memory.clear(_memory_key(user, req.anon_id), subject=req.subject)
    return {"ok": True}
