"""POST /api/chat — streaming chat agent endpoint."""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..agent.planner import stream_chat
from ..auth import CurrentUser, get_optional_user
from ..schemas import ChatRequest

router = APIRouter()


@router.post("/chat")
def chat(
    req: ChatRequest,
    user: CurrentUser | None = Depends(get_optional_user),
):
    """Handle one user chat message, streaming reply as NDJSON."""
    user_id = user.id if user else None
    return StreamingResponse(
        stream_chat(req.message, req.conversation_id, user_id=user_id),
        media_type="application/x-ndjson",
    )

