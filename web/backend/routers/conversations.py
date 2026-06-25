"""GET /api/conversations — list and detail endpoints for past consultations."""
from fastapi import APIRouter, Depends, HTTPException, Query

from ..agent.repository import (
    get_conversation,
    get_conversation_messages,
    get_conversation_state,
    list_conversations,
)
from ..auth import CurrentUser, get_optional_user

router = APIRouter()


def _owner_key(user: CurrentUser | None, anon_id: str | None) -> str | None:
    """Logged-in user id, else the anonymous client id."""
    return (user.id if user else None) or anon_id


@router.get("/conversations")
def conversations_list(
    anon_id: str | None = Query(default=None),
    user: CurrentUser | None = Depends(get_optional_user),
):
    """List the requesting owner's conversations only."""
    return list_conversations(limit=50, user_id=_owner_key(user, anon_id))


@router.get("/conversations/{conversation_id}")
def conversation_detail(
    conversation_id: str,
    anon_id: str | None = Query(default=None),
    user: CurrentUser | None = Depends(get_optional_user),
):
    """Return a single conversation with its messages and parsed state."""
    conversation = get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话未找到")

    if conversation.get("user_id") != _owner_key(user, anon_id):
        raise HTTPException(status_code=404, detail="会话未找到")

    messages = get_conversation_messages(conversation_id)
    if not messages:
        raise HTTPException(status_code=404, detail="会话未找到")
    state = get_conversation_state(conversation_id)
    return {
        "conversation_id": conversation_id,
        "messages": messages,
        "state": state,
    }
