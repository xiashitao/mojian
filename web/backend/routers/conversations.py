"""GET /api/conversations — list and detail endpoints for past consultations."""
from fastapi import APIRouter, HTTPException

from ..agent.repository import (
    get_conversation_messages,
    get_conversation_state,
    list_conversations,
)

router = APIRouter()


@router.get("/conversations")
def conversations_list():
    """List all active conversations, most recent first."""
    return list_conversations(limit=50)


@router.get("/conversations/{conversation_id}")
def conversation_detail(conversation_id: str):
    """Return a single conversation with its messages and parsed state."""
    messages = get_conversation_messages(conversation_id)
    if not messages:
        # Could be a brand-new conversation that only exists client-side
        raise HTTPException(status_code=404, detail="会话未找到")
    state = get_conversation_state(conversation_id)
    return {
        "conversation_id": conversation_id,
        "messages": messages,
        "state": state,
    }
