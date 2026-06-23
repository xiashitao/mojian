"""POST /api/chat — chat-first bazibase agent endpoint."""
from fastapi import APIRouter, HTTPException

from ..agent.planner import handle_chat
from ..schemas import ChatRequest

router = APIRouter()


@router.post("/chat")
def chat(req: ChatRequest):
    """Handle one user chat message."""
    try:
        return handle_chat(req.message, req.conversation_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

