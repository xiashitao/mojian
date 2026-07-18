"""GET /api/conversations — list and detail endpoints for past consultations."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..agent.repository import (
    get_conversation,
    get_conversation_messages,
    get_conversation_state,
    list_conversations,
    set_message_feedback,
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


class FeedbackIn(BaseModel):
    """一轮回复的用户反馈。以 analysis_id 为键(流式期间前端消息是临时 id,
    只有 analysis_id 稳定);feedback=None 表示撤销。"""

    analysis_id: str
    feedback: Literal["like", "dislike"] | None = None
    comment: str | None = Field(default=None, max_length=500)
    anon_id: str | None = None  # 匿名用户的归属键(与 GET 的 query 参数同源)


@router.post("/feedback")
def submit_feedback(
    body: FeedbackIn,
    user: CurrentUser | None = Depends(get_optional_user),
):
    """记录/撤销用户对某轮回复的反馈。归属校验:只能反馈自己会话里的轮次。"""
    result = set_message_feedback(
        body.analysis_id,
        owner_key=_owner_key(user, body.anon_id),
        feedback=body.feedback,
        comment=body.comment,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="该轮分析未找到")
    return result


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
