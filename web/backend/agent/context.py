"""Context engineering: decide WHAT goes into the model's context and HOW MUCH.

Centralises the prompt's variable context — relevance-ranked memory notes,
budgeted recent history, and the topic label — so it stays focused and bounded
as memory and conversation history grow, instead of blindly concatenating.
"""
from __future__ import annotations

import re
from typing import Any

from .topics import topic_cn  # noqa: F401 — re-export; 定义已移入话题注册表

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

# 笔记检索权重(select_notes 有 query 时)。设计意图:词法命中是强信号——
# 用户这句话里提到的事,比「同话题标签」更该被想起(跨话题的关键旧信息,
# 如问健康时提到过的家人病史,靠它捞回来);话题标签是弱先验;时间是并列时
# 的裁决。全部确定性计算,零外部依赖——检索升级阶梯的下一级才是 FTS5/向量。
# 标定依据:整句中文的 bigram Dice 实测天花板 ~0.2-0.4(共享词组被句子长度
# 稀释),所以词法权重必须让 sim≈0.25(一个关键词组命中)就能压过
# 「话题匹配 + 最新」的底分(0.3+0.2);test_retrieval.py 用真实句子钉住这条。
_W_TOPIC = 0.3      # 话题标签匹配
_W_LEXICAL = 2.5    # 字符 bigram Dice 相似度(中文短文本免分词的标准做法)
_W_RECENCY = 0.2    # 1/(1+新旧序) 衰减
_DEDUP_SIM = 0.85   # 近重复折叠阈值:两条笔记相似度超过它,只留最新一条


def _norm(text: str) -> str:
    """归一化:去空白/标点、转小写(\\w 在 py3 里含 CJK,中文原样保留)。"""
    return re.sub(r"[\W_]+", "", str(text or "").lower())


def _bigrams(text: str) -> set[str]:
    t = _norm(text)
    if len(t) < 2:
        return {t} if t else set()
    return {t[i:i + 2] for i in range(len(t) - 1)}


def _lexical_sim(a_grams: set[str], b_grams: set[str]) -> float:
    """Dice 系数 ∈ [0,1]。bigram 级别的重叠对中文短文本足够灵敏。"""
    if not a_grams or not b_grams:
        return 0.0
    inter = len(a_grams & b_grams)
    if not inter:
        return 0.0
    return 2 * inter / (len(a_grams) + len(b_grams))


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
    query: str = "",
    max_notes: int = NOTES_MAX,
    char_budget: int = NOTES_CHAR_BUDGET,
) -> list[dict[str, Any]]:
    """Memory notes ranked by relevance, within a budget.

    检索分两档:
    - 有 query(用户当前消息):多信号打分 = 词法相似(bigram Dice)+ 话题
      标签 + 时间衰减——用户这句话提到的旧信息能跨话题被捞回来;
    - 无 query:保持原行为(同话题优先、新在前),兼容不带查询的调用方。
    两档共用近重复折叠:内容高度相似的笔记只留最新一条(存储侧 reflect 去重
    之外的第二道闸,老的重复数据也能被挡住)。
    """
    if not notes:
        return []
    # 近重复折叠(输入新→旧,保留最先出现的 = 最新的)
    kept: list[dict[str, Any]] = []
    kept_grams: list[set[str]] = []
    for n in notes:
        if not _has_content(n):
            continue
        grams = _bigrams(_note_line(n))
        if any(_lexical_sim(grams, g) >= _DEDUP_SIM for g in kept_grams):
            continue
        kept.append(n)
        kept_grams.append(grams)

    q_grams = _bigrams(query)
    if not q_grams:
        same = [n for n in kept if n.get("topic") == topic]
        other = [n for n in kept if n.get("topic") != topic]
        ordered = same + other  # each list is already newest-first from the store
    else:
        scored = []  # (负分, 新旧序, 笔记):sort 后高分在前,同分新的在前
        for rank, (n, grams) in enumerate(zip(kept, kept_grams)):
            s = (_W_TOPIC * (1.0 if n.get("topic") == topic else 0.0)
                 + _W_LEXICAL * _lexical_sim(q_grams, grams)
                 + _W_RECENCY / (1 + rank))
            scored.append((-s, rank, n))
        scored.sort(key=lambda t: (t[0], t[1]))
        ordered = [n for _, _, n in scored]

    picked: list[dict[str, Any]] = []
    used = 0
    for note in ordered[:max_notes]:
        length = len(_note_line(note))  # 预算按渲染后的完整行算(含记忆)
        if picked and used + length > char_budget:
            break
        picked.append(note)
        used += length
    return picked


def render_notes(notes: list[dict[str, Any]] | None, topic: str | None,
                 *, query: str = "") -> str:
    """渲染笔记块。query 会让排序随每轮消息变化——不用担心缓存:每轮咨询后
    都会追加新笔记,这个块本来就逐轮变化,查询感知排序不增加缓存失效面。"""
    lines: list[str] = []
    for note in select_notes(notes, topic, query=query):
        line = _note_line(note)
        label = topic_cn(note["topic"]) if note.get("topic") else ""
        lines.append(f"[{label}] {line}" if label else line)
    return "\n".join(lines)


def _note_line(note: dict[str, Any]) -> str:
    """一条笔记的渲染:结论 +(可选)agent 自主记忆。

    memory_text 记「用户是个什么情况」(处境/计划/事实),缀在结论后,
    让回访时模型知道上次用户透露过什么。"""
    conclusion = str(note.get("conclusion", "")).strip()
    memory = str(note.get("memory_text") or "").strip()
    if conclusion and memory:
        return f"{conclusion}（用户情况：{memory}）"
    return conclusion or f"（用户情况：{memory}）"


def _has_content(note: dict[str, Any]) -> bool:
    return bool(str(note.get("conclusion", "")).strip()
                or str(note.get("memory_text") or "").strip())


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
