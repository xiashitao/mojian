"""Pydantic models used inside the chat agent."""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Literal


Intent = Literal[
    "collect_birth_info",
    "career",
    "relationship",
    "wealth",
    "personality",
    "clarify_previous",
    "smalltalk",
    "out_of_scope",
    "unknown",
]

Topic = Literal["career", "relationship", "wealth", "personality"]

# The single dispatchable decision the planner acts on.
Action = Literal[
    "smalltalk",
    "out_of_scope",
    "clarify",
    "ask_birth_info",
    "ask_topic",
    "consult",
]


class BirthInfo(BaseModel):
    birth_date: str | None = None
    birth_time: str | None = None
    birth_place: str | None = None
    longitude: float | None = None
    gender: Literal["male", "female"] | None = None
    tz_offset_hours: float = 8.0
    apply_solar_time_correction: bool = True
    confidence: float = 0.0
    missing_fields: list[str] = Field(default_factory=list)

    def complete_missing_fields(self) -> list[str]:
        missing: list[str] = []
        if not self.birth_date:
            missing.append("birth_date")
        if not self.birth_time:
            missing.append("birth_time")
        if self.longitude is None:
            missing.append("birth_place")
        if not self.gender:
            missing.append("gender")
        return missing

    def is_complete(self) -> bool:
        return not self.complete_missing_fields()


class ExtractionResult(BaseModel):
    intent: Intent = "unknown"
    topic: Topic | None = None
    birth_info: BirthInfo = Field(default_factory=BirthInfo)
    raw_text: str


class ConversationState(BaseModel):
    birth_info: BirthInfo = Field(default_factory=BirthInfo)
    current_topic: Topic | None = None
    last_analysis_id: str | None = None
    # Birth key the chart card was already shown for (so it's not repeated).
    chart_shown_for: str | None = None
    source_basis: dict[str, Any] = Field(default_factory=lambda: {
        "primary_source": "子平真诠",
        "secondary_sources": ["滴天髓"],
        "source_tensions": [],
    })


class ChatState(BaseModel):
    topic: Topic | None = None
    needs_more_info: bool
    missing_fields: list[str] = Field(default_factory=list)
    suggested_followups: list[str] = Field(default_factory=list)


class RouteDecision(BaseModel):
    """The router's output: one action plus the resolved routing context."""
    action: Action
    intent: Intent = "unknown"
    topic: Topic | None = None
    birth_info: BirthInfo = Field(default_factory=BirthInfo)
    missing_fields: list[str] = Field(default_factory=list)


class ToolBundle(BaseModel):
    chart: dict[str, Any] | None = None
    diagnosis: dict[str, Any] | None = None
    arbitration: dict[str, Any] | None = None

