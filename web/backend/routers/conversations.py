"""GET /api/conversations — list and detail endpoints for past consultations."""
from fastapi import APIRouter, Depends, HTTPException

from ..agent.repository import (
    get_conversation_messages,
    get_conversation_state,
    list_conversations,
)
from ..auth import CurrentUser, get_optional_user

router = APIRouter()


@router.get("/conversations")
def conversations_list(user: CurrentUser | None = Depends(get_optional_user)):
    """List conversations for the current user (or all if no auth)."""
    user_id = user.id if user else None
    return list_conversations(limit=50, user_id=user_id)


@router.get("/conversations/{conversation_id}")
def conversation_detail(conversation_id: str):
    """Return a single conversation with its messages and parsed state."""
    messages = get_conversation_messages(conversation_id)
    if not messages:
        raise HTTPException(status_code=404, detail="会话未找到")
    state = get_conversation_state(conversation_id)
    return {
        "conversation_id": conversation_id,
        "messages": messages,
        "state": state,
    }
