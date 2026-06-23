"""Admin inspection endpoints for agent analyses."""
from fastapi import APIRouter, HTTPException

from ..agent.repository import get_analysis_package

router = APIRouter(prefix="/admin")


@router.get("/analyses/{analysis_id}")
def get_analysis(analysis_id: str):
    """Return the full trace package for one public analysis ID.

    This endpoint is intended for operations/internal use. Add auth before
    exposing it outside local development.
    """
    package = get_analysis_package(analysis_id)
    if package is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return package

