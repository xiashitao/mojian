"""Admin inspection endpoints for agent analyses."""
from fastapi import APIRouter, Depends, HTTPException

from ..agent.repository import get_analysis_package
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

