"""POST /api/chat — streaming chat agent endpoint."""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..agent.planner import stream_chat
# TEMP(login-gate disabled): allow anonymous chat.
# To re-gate, restore `get_current_user` and the `user: CurrentUser` dep below.
from ..auth import CurrentUser, get_optional_user  # get_current_user
from ..schemas import ChatRequest

router = APIRouter()


@router.post("/chat")
def chat(
    req: ChatRequest,
    # TEMP: was `user: CurrentUser = Depends(get_current_user)` (login required)
    user: CurrentUser | None = Depends(get_optional_user),
):
    """Handle one user chat message, streaming reply as NDJSON.

    TEMP: login gate disabled — anonymous chatting allowed again. Memory and
    conversations are keyed to the account when signed in, else the anon id.
    """
    user_id = user.id if user else None
    memory_key = user_id or req.anon_id
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

