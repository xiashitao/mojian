"""POST /api/chat — streaming chat agent endpoint."""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..agent.planner import stream_chat
from ..schemas import ChatRequest

router = APIRouter()


@router.post("/chat")
def chat(req: ChatRequest):
    """Handle one user chat message, streaming reply as NDJSON."""
    return StreamingResponse(
        stream_chat(req.message, req.conversation_id),
        media_type="application/x-ndjson",
    )

