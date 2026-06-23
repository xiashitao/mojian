"""GET/POST/DELETE /api/charts — saved chart CRUD."""
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from ..database import get_db
from ..schemas import SaveChartRequest

router = APIRouter(prefix="/charts")


@router.get("")
def list_charts(q: Optional[str] = Query(None, description="Search label")):
    """List all saved charts, optionally filtered by label."""
    conn = get_db()
    try:
        if q:
            rows = conn.execute(
                "SELECT * FROM saved_charts WHERE label LIKE ? ORDER BY created_at DESC",
                (f"%{q}%",),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM saved_charts ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.post("")
def save_chart(req: SaveChartRequest):
    """Save a new chart."""
    chart_id = str(uuid.uuid4())[:8]
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO saved_charts
               (id, label, date, time, longitude, gender, tz_offset, solar_correction)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (chart_id, req.label, req.date, req.time, req.longitude,
             req.gender, req.tz_offset, int(req.solar_correction)),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM saved_charts WHERE id = ?", (chart_id,)
        ).fetchone()
        return dict(row)
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.delete("/{chart_id}")
def delete_chart(chart_id: str):
    """Delete a saved chart."""
    conn = get_db()
    try:
        cursor = conn.execute(
            "DELETE FROM saved_charts WHERE id = ?", (chart_id,)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Chart not found")
        return {"deleted": chart_id}
    finally:
        conn.close()
