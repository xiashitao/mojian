"""Routing layer: turn a user message + conversation state into one action.

The LLM (via `extract_message`) owns the *semantic* routing — greeting,
out-of-scope, clarify, which topic, whether birth info is being given. The
state-dependent gating (is birth info complete yet? has a topic been chosen?)
stays deterministic here on purpose: that bookkeeping must be reliable, and
LLMs are weak at it. The planner then simply dispatches on `decision.action`.
"""
from __future__ import annotations

from .extractor import extract_message, merge_birth_info
from .models import Action, BirthInfo, ConversationState, RouteDecision, Topic


def route(message: str, state: ConversationState, *, trace_sink=None) -> RouteDecision:
    """Decide the next action for a user message given the conversation state."""
    extraction = extract_message(message, trace_sink=trace_sink)
    birth_info = merge_birth_info(state.birth_info, extraction.birth_info)
    topic = extraction.topic or state.current_topic
    action = _action_for(extraction.intent, topic, birth_info, extraction.subject)
    # subject_confidence:有明确值(self/spouse/...)为高;unknown/None 视情况。
    # 用作 planner 是否触发前端确认的参考(此处主要靠 action=confirm_subject)。
    subj = extraction.subject
    subj_conf = 0.0 if subj in (None, "unknown") else 0.9
    return RouteDecision(
        action=action,
        intent=extraction.intent,
        topic=topic,
        birth_info=birth_info,
        missing_fields=birth_info.complete_missing_fields(),
        subject=subj,
        subject_confidence=subj_conf,
    )


def _action_for(
    intent: str,
    topic: Topic | None,
    birth_info: BirthInfo,
    subject: str | None = None,
) -> Action:
    # Semantic routes from the extractor win regardless of stored state.
    if intent == "smalltalk":
        return "smalltalk"
    if intent == "out_of_scope":
        return "out_of_scope"
    # Everything below needs a complete chart to say anything.
    if not birth_info.is_complete():
        return "ask_birth_info"
    # 八字齐全但「不知道是谁的」:先确认主体,再排盘。避免用错八字。
    # 注意:只在用户**本轮提供了生辰**且 subject 明确为 unknown 时触发;
    # 已有完整 birth_info 的后续咨询(subject=None,沿用会话主体)不重复问。
    if subject == "unknown":
        return "confirm_subject"
    if intent == "clarify_previous":
        return "clarify"
    # Only ask which direction when the user *just gave birth info* with no
    # question. A real but unclassified question (e.g. "我的学历"，topic 不在四类
    # 里) should be answered, not bounced back — 下游 actual_topic 会兜底默认话题。
    if topic is None and intent == "collect_birth_info":
        return "ask_topic"
    return "consult"
