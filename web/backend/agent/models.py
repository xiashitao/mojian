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

# 命盘主体:这套八字是谁的。同一用户可为多人各存一套八字/画像/笔记。
# self=用户本人,spouse=配偶,child=子女,parent=父母,other=其他(朋友/合作方等)。
# MVP 不区分多个同类主体(两个儿子=后报覆盖先报)。
Subject = Literal["self", "spouse", "child", "parent", "other"]

# The single dispatchable decision the planner acts on.
Action = Literal[
    "smalltalk",
    "out_of_scope",
    "clarify",
    "ask_birth_info",
    "ask_topic",
    "confirm_subject",  # 八字完整但主体不明,需要用户确认这是谁的
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
    # 这套八字是谁的。默认 self(用户本人);其他值需 extractor 从对话识别
    # ("我儿子的"→child)或前端弹表单让用户确认。详见 Subject 定义。
    subject: Subject = "self"

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
    # extractor 对主体的判断:None=未抽到生辰;"unknown"=有生辰但关系不明;
    # self/spouse/child/parent/other=明确识别。用 str 而非 Subject,因为
    # "unknown" 是中间状态不进存储枚举。
    subject: str | None = None


class ConversationState(BaseModel):
    birth_info: BirthInfo = Field(default_factory=BirthInfo)
    current_topic: Topic | None = None
    # 当前会话在聊谁。会话内可切换主体;切换后 birth_info/画像/笔记按它隔离重载。
    current_subject: Subject = "self"
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
    # extractor 对主体的判断:None=未抽到生辰(无关主体);
    # "unknown"=出现了生辰但关系不明(router 据此触发 confirm_subject);
    # self/spouse/child/parent/other=明确识别。"unknown" 是 extractor 的
    # 中间状态,不进 Subject 枚举(那是存储用的),故这里用更宽的 str 类型。
    subject: str | None = None
    subject_confidence: float = 0.0


class ToolBundle(BaseModel):
    chart: dict[str, Any] | None = None
    diagnosis: dict[str, Any] | None = None
    arbitration: dict[str, Any] | None = None


class UserProfile(BaseModel):
    """沉淀的用户画像:从历次咨询里提取的稳定特征。

    用于让回答更贴合「这个人是谁」:人生阶段决定建议的现实约束,
    核心关切决定侧重,性格决定语气,沟通偏好决定表达方式。

    所有字段都可空——画像是从对话里逐步累积的,不会一开始就完整。
    LLM 只在出现明确信号时才填/更新字段,绝不臆测。
    """

    life_stage: str | None = None
    """人生阶段,如「在校」「职场初期」「职业转型期」「创业」「退休」等。"""

    core_concerns: list[str] = Field(default_factory=list)
    """核心关切,如 ["职业方向","婚姻","父母健康"]。来自用户反复追问的话题。"""

    traits: list[str] = Field(default_factory=list)
    """性格关键词,如 ["谨慎","重家庭","理想主义"]。从言谈和决策倾向里提取。"""

    long_term_goal: str | None = None
    """长期目标(一句话),如「希望在 35 岁前完成职业转型」。"""

    comm_style: str | None = None
    """沟通偏好,如「直接」「委婉」「理性」「感性」。决定回答的语气。"""

    raw_summary: str | None = None
    """LLM 生成的补充描述(可选),用于放结构化字段装不下的细节。"""

    def is_empty(self) -> bool:
        """是否完全空白(没有任何已识别的字段)。"""
        return not (
            self.life_stage
            or self.core_concerns
            or self.traits
            or self.long_term_goal
            or self.comm_style
            or (self.raw_summary and self.raw_summary.strip())
        )

