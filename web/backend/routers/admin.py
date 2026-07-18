"""Admin inspection endpoints for agent analyses."""
from fastapi import APIRouter, Depends, HTTPException, Query

from ..agent.repository import (
    get_analysis_package,
    get_conversation,
    get_conversation_messages,
    get_conversation_runs,
    list_feedback,
    recent_runs,
)
from ..auth import CurrentUser, require_admin

router = APIRouter(prefix="/admin")


@router.get("/analyses/{analysis_id}")
def get_analysis(
    analysis_id: str,
    _: CurrentUser = Depends(require_admin),
):
    """Return the full trace package for one public analysis ID. Admin only."""
    package = get_analysis_package(analysis_id)
    if package is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return package


@router.get("/conversations/{conversation_id}/runs")
def list_conversation_runs(
    conversation_id: str,
    _: CurrentUser = Depends(require_admin),
):
    """一段会话里每轮 run 的概要 + LLM 聚合,支撑跨轮追踪时间线。Admin only."""
    return {"runs": get_conversation_runs(conversation_id)}


@router.get("/feedback")
def feedback_list(
    days: int = Query(default=30, ge=1, le=365),
    _: CurrentUser = Depends(require_admin),
):
    """近期用户反馈(赞/踩/评论),每条带 analysis_id 直达该轮 trace。Admin only."""
    return {"feedback": list_feedback(days=days)}


@router.get("/runs")
def runs_recent(
    limit: int = Query(default=30, ge=1, le=200),
    _: CurrentUser = Depends(require_admin),
):
    """最近 N 轮 run 概要(运营后台的浏览入口)。Admin only."""
    return {"runs": recent_runs(limit=limit)}


@router.get("/conversations/{conversation_id}")
def admin_conversation_detail(
    conversation_id: str,
    _: CurrentUser = Depends(require_admin),
):
    """运营视角的会话详情:完整消息流 + 逐轮概要(含成本)。Admin only。

    与用户侧 /conversations/{id} 的区别:不做归属过滤(运营要看所有用户的
    会话),并附 runs(每轮 intent/耗时/token/cost,前端据此渲染元信息条)。
    """
    conversation = get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话未找到")
    return {
        "conversation": conversation,
        "messages": get_conversation_messages(conversation_id),
        "runs": get_conversation_runs(conversation_id),
    }

