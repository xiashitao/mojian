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


def route(message: str, state: ConversationState) -> RouteDecision:
    """Decide the next action for a user message given the conversation state."""
    extraction = extract_message(message)
    birth_info = merge_birth_info(state.birth_info, extraction.birth_info)
    topic = extraction.topic or state.current_topic
    action = _action_for(extraction.intent, topic, birth_info)
    return RouteDecision(
        action=action,
        intent=extraction.intent,
        topic=topic,
        birth_info=birth_info,
        missing_fields=birth_info.complete_missing_fields(),
    )


def _action_for(intent: str, topic: Topic | None, birth_info: BirthInfo) -> Action:
    # Semantic routes from the extractor win regardless of stored state.
    if intent == "smalltalk":
        return "smalltalk"
    if intent == "out_of_scope":
        return "out_of_scope"
    # Everything below needs a complete chart to say anything.
    if not birth_info.is_complete():
        return "ask_birth_info"
    if intent == "clarify_previous":
        return "clarify"
    if topic is None and intent in ("collect_birth_info", "unknown"):
        return "ask_topic"
    return "consult"
