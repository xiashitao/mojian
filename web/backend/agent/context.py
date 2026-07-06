"""Context engineering: decide WHAT goes into the model's context and HOW MUCH.

Centralises the prompt's variable context — relevance-ranked memory notes,
budgeted recent history, and the topic label — so it stays focused and bounded
as memory and conversation history grow, instead of blindly concatenating.
"""
from __future__ import annotations

from typing import Any

_ROLE_CN = {"user": "用户", "assistant": "助手"}

# Char budgets — Chinese text is roughly a couple of characters per token.
# Loosened from 6/1400 now that the big analysis block is prefix-cached, so the
# variable history is the marginal cost and a wider window is cheap.
HISTORY_MAX_TURNS = 8
HISTORY_CHAR_BUDGET = 2000
# The last few turns stay (near-)verbatim; older assistant turns compress to
# their one-line 结论 (which reflect_on_reply already produced) instead of being
# blindly truncated mid-sentence — a 300–500 字 reply cut to ~200 lost exactly
# the conclusions the model needs to avoid repeating itself.
HISTORY_RECENT_FULL = 2
HISTORY_FULL_CAP = 360   # recent turns — room for a whole assistant reply
HISTORY_OLD_CAP = 160    # older turns with no 结论 to fall back on
NOTES_MAX = 4
NOTES_CHAR_BUDGET = 600


def topic_cn(topic: str | None) -> str:
    return {
        "career": "事业",
        "relationship": "感情",
        "wealth": "财务",
        "personality": "性格",
    }.get(topic or "career", "这个问题")


def _render_turn(msg: dict[str, Any], *, full: bool) -> str:
    content = str(msg.get("content", "")).strip()
    if not content:
        return ""
    # Older assistant turns: prefer the stored one-line 结论 over a blind cut.
    if not full and str(msg.get("role")) == "assistant":
        conclusion = str(msg.get("conclusion", "")).strip()
        if conclusion:
            content = conclusion
    cap = HISTORY_FULL_CAP if full else HISTORY_OLD_CAP
    if len(content) > cap:
        content = content[:cap] + "…"
    role = _ROLE_CN.get(str(msg.get("role")), str(msg.get("role")))
    return f"{role}：{content}"


def render_history(
    history: list[dict[str, Any]] | None,
    *,
    max_turns: int = HISTORY_MAX_TURNS,
    char_budget: int = HISTORY_CHAR_BUDGET,
) -> str:
    """Recent turns within a char budget; oldest dropped first to fit. The last
    HISTORY_RECENT_FULL turns are kept (near-)verbatim; older assistant turns
    collapse to their 结论 so meaning survives the budget instead of a mid-cut."""
    if not history:
        return ""
    window = history[-max_turns:]
    n = len(window)
    lines: list[str] = []
    for i, msg in enumerate(window):
        full = i >= n - HISTORY_RECENT_FULL
        line = _render_turn(msg, full=full)
        if line:
            lines.append(line)
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


def render_profile(profile) -> str:
    """Render a UserProfile into a compact, natural-language block for the prompt.

    Empty profile → empty string (caller skips the section). Designed to slot
    into user_prompt right before 过往咨询记录:profile is stable-ish (changes
    every N turns) so it sits in the cacheable middle of the prompt, ahead of
    the per-turn history/question tail.

    Kept deliberately short and factual — the model should *use* it as context,
    not parrot it. Style: reads like a one-paragraph briefing about the user.
    """
    if profile is None or profile.is_empty():
        return ""

    parts: list[str] = []

    if profile.life_stage:
        parts.append(f"人生阶段：{profile.life_stage}")
    if profile.core_concerns:
        parts.append(f"核心关切：{'、'.join(profile.core_concerns)}")
    if profile.traits:
        parts.append(f"性格特征：{'、'.join(profile.traits)}")
    if profile.long_term_goal:
        parts.append(f"长期目标：{profile.long_term_goal}")
    if profile.comm_style:
        parts.append(f"沟通偏好：{profile.comm_style}")
    if profile.raw_summary and profile.raw_summary.strip():
        parts.append(profile.raw_summary.strip())

    return "；".join(parts) + "。" if parts else ""
