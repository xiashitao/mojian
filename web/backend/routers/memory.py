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
def get_remembered_birth_info(
    req: MemoryRequest,
    user: CurrentUser | None = Depends(get_optional_user),
):
    """Return the remembered birth info (or null) for this user."""
    info = memory.get_birth_info(_memory_key(user, req.anon_id))
    return {"birth_info": info.dict() if info else None}


@router.post("/memory/forget")
def forget(
    req: MemoryRequest,
    user: CurrentUser | None = Depends(get_optional_user),
):
    """Clear everything remembered for this user."""
    memory.clear(_memory_key(user, req.anon_id))
    return {"ok": True}
