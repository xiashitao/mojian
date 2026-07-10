"""Admin inspection endpoints for agent analyses."""
from fastapi import APIRouter, Depends, HTTPException

from ..agent.repository import get_analysis_package, get_conversation_runs
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

