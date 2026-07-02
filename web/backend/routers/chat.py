"""POST /api/chat — streaming chat agent endpoint."""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..agent.planner import stream_chat
from ..auth import CurrentUser, get_current_user
from ..schemas import ChatRequest

router = APIRouter()


@router.post("/chat")
def chat(
    req: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Handle one user chat message, streaming reply as NDJSON.

    Login required: anonymous requests get 401 (the frontend catches it and
    opens the login modal). Memory and conversations are keyed to the account.
    """
    user_id = user.id
    memory_key = user_id
    return StreamingResponse(
        stream_chat(
            req.message,
            req.conversation_id,
            user_id=user_id,
            memory_key=memory_key,
            tone=req.tone,
        ),
        media_type="application/x-ndjson",
    )

