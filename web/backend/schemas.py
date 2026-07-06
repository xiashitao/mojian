"""Pydantic request models. Responses use bazibase's .to_dict() directly."""
from pydantic import BaseModel, Field
from typing import Optional


class ChartRequest(BaseModel):
    """POST /api/chart request body."""
    date: str = Field(..., description="YYYY-MM-DD")
    time: str = Field(..., description="HH:MM or HH:MM:SS")
    longitude: float = Field(..., description="出生地经度")
    gender: str = Field("male", description="male | female")
    tz_offset_hours: float = Field(8.0, description="UTC offset")
    apply_solar_time_correction: bool = Field(True, description="真太阳时修正")


class ArbitrateRequest(ChartRequest):
    """POST /api/arbitrate request body."""
    threshold: float = Field(0.6, description="置信度阈值")


class SaveChartRequest(BaseModel):
    """POST /api/charts request body."""
    label: str
    date: str
    time: str
    longitude: float
    gender: str
    tz_offset: float = 8.0
    solar_correction: bool = True


class ChatRequest(BaseModel):
    """POST /api/chat request body."""
    message: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None
    anon_id: Optional[str] = None
    # Answer tone preset (advisor | friend | direct). Only the wording style;
    # unknown / None falls back to the restrained default in the responder.
    tone: Optional[str] = None
    # 命盘主体:由前端"确认主体"对话框回传(self/spouse/child/parent/other)。
    # 后端检测到八字但主体不明时会先返回 needs_subject_confirmation 事件,
    # 用户在前端选完主体后,带这个字段重新发请求。None=沿用会话当前主体。
    subject: Optional[str] = None
