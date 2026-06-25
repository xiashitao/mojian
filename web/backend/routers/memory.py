"""User memory endpoints — view / clear remembered birth info."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..agent import memory
from ..auth import CurrentUser, get_optional_user

router = APIRouter()


class MemoryRequest(BaseModel):
    anon_id: str | None = None


def _memory_key(user: CurrentUser | None, anon_id: str | None) -> str | None:
    return (user.id if user else None) or anon_id


@router.post("/memory/birth-info")
def get_remembered_memory(
    req: MemoryRequest,
    user: CurrentUser | None = Depends(get_optional_user),
):
    """Return what we remember about this user: birth info + recent notes."""
    key = _memory_key(user, req.anon_id)
    info = memory.get_birth_info(key)
    return {
        "birth_info": info.model_dump() if info else None,
        "notes": memory.recent_notes(key),
    }


@router.post("/memory/forget")
def forget(
    req: MemoryRequest,
    user: CurrentUser | None = Depends(get_optional_user),
):
    """Clear everything remembered for this user."""
    memory.clear(_memory_key(user, req.anon_id))
    return {"ok": True}
