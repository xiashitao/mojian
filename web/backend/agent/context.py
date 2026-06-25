"""Context engineering: decide WHAT goes into the model's context and HOW MUCH.

Centralises the prompt's variable context — relevance-ranked memory notes,
budgeted recent history, and the topic label — so it stays focused and bounded
as memory and conversation history grow, instead of blindly concatenating.
"""
from __future__ import annotations

from typing import Any

_ROLE_CN = {"user": "用户", "assistant": "助手"}

# Char budgets — Chinese text is roughly a couple of characters per token.
HISTORY_MAX_TURNS = 6
HISTORY_CHAR_BUDGET = 1400
HISTORY_TURN_CHAR_CAP = 200
NOTES_MAX = 4
NOTES_CHAR_BUDGET = 600


def topic_cn(topic: str | None) -> str:
    return {
        "career": "事业",
        "relationship": "感情",
        "wealth": "财务",
        "personality": "性格",
    }.get(topic or "career", "这个问题")


def render_history(
    history: list[dict[str, Any]] | None,
    *,
    max_turns: int = HISTORY_MAX_TURNS,
    char_budget: int = HISTORY_CHAR_BUDGET,
) -> str:
    """Most recent turns within a char budget; oldest dropped first to fit."""
    if not history:
        return ""
    lines: list[str] = []
    for msg in history[-max_turns:]:
        content = str(msg.get("content", "")).strip()
        if not content:
            continue
        if len(content) > HISTORY_TURN_CHAR_CAP:
            content = content[:HISTORY_TURN_CHAR_CAP] + "…"
        role = _ROLE_CN.get(str(msg.get("role")), str(msg.get("role")))
        lines.append(f"{role}：{content}")
    while len(lines) > 1 and sum(len(x) for x in lines) > char_budget:
        lines.pop(0)
    return "\n".join(lines)


def select_notes(
    notes: list[dict[str, Any]] | None,
    topic: str | None,
    *,
    max_notes: int = NOTES_MAX,
    char_budget: int = NOTES_CHAR_BUDGET,
) -> list[dict[str, Any]]:
    """Memory notes ranked by relevance (same topic first), within a budget."""
    if not notes:
        return []
    same = [n for n in notes if _has_conclusion(n) and n.get("topic") == topic]
    other = [n for n in notes if _has_conclusion(n) and n.get("topic") != topic]
    ordered = same + other  # each list is already newest-first from the store
    picked: list[dict[str, Any]] = []
    used = 0
    for note in ordered[:max_notes]:
        length = len(str(note.get("conclusion", "")).strip())
        if picked and used + length > char_budget:
            break
        picked.append(note)
        used += length
    return picked


def render_notes(notes: list[dict[str, Any]] | None, topic: str | None) -> str:
    lines: list[str] = []
    for note in select_notes(notes, topic):
        conclusion = str(note.get("conclusion", "")).strip()
        label = topic_cn(note["topic"]) if note.get("topic") else ""
        lines.append(f"[{label}] {conclusion}" if label else conclusion)
    return "\n".join(lines)


def _has_conclusion(note: dict[str, Any]) -> bool:
    return bool(str(note.get("conclusion", "")).strip())
