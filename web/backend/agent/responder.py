"""User-facing response generation for the MVP chat agent."""
from __future__ import annotations

import json
import re
from collections.abc import Iterator
from typing import Any

from bazibase.constants import ELEMENT_CONQUEST, ELEMENT_PRODUCTION
from bazibase.rules.fortune import ROLE_PLAIN

from ..services.llm import LLMError, complete, fast_provider, is_configured, stream
from .context import render_history
from .models import BirthInfo, ChatState, Topic, UserProfile
from .prompt_registry import DEFAULT_TONE, build_turn_ctx, compose  # noqa: F401 - DEFAULT_TONE re-export(历史调用方)
from .topics import topic_cn, topic_spec


_FIELD_CN = {
    "birth_date": "出生年月日",
    "birth_time": "出生时间",
    "birth_place": "出生地",
    "gender": "性别",
}

# ── Grounding guardrail ──────────────────────────────────────────────────────
# The engine is authoritative; the LLM only does wording. These deterministic
# checks catch the model contradicting / leaking the engine's facts so we can
# record it on the run trace (monitoring + regression signal for the eval set).
# Policy A: core 十神 terms are allowed (with a plain-language gloss) for depth,
# so we no longer flag them — only raw 干支 dumps and age contradictions.
_GANZHI_RE = re.compile(r"[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]")
# "今年/现在/目前/当前 … N 岁" — the person's *current* age claim, the spot the
# model is most likely to invent (e.g. saying 周岁 30 when the chart is 虚岁 31).
_CURRENT_AGE_RE = re.compile(r"(?:今年|现在|目前|当前)[^。，；！？\n]{0,8}?(\d{1,3})\s*岁")


def check_grounding(reply: str, context: dict[str, Any]) -> list[str]:
    """Return a list of grounding violations in a generated reply.

    Deterministic and conservative (low false-positive). Non-blocking: callers
    record the result on the trace rather than rejecting the (already-streamed)
    reply. Also reusable by the eval harness.
    """
    violations: list[str] = []

    ganzhi = sorted(set(_GANZHI_RE.findall(reply)))
    if ganzhi:
        violations.append("泄漏干支术语：" + "、".join(ganzhi))

    cp = context.get("current_period") or {}
    nominal = cp.get("nominal_age")
    if isinstance(nominal, int):
        # The chart presents 虚岁 everywhere, so the prose must too — a bare
        # 周岁 (虚岁-1) reads as the inconsistency users notice. If the 虚岁/周岁
        # product convention changes, update this anchor with the chart.
        for m in _CURRENT_AGE_RE.finditer(reply):
            said = int(m.group(1))
            if said != nominal:
                violations.append(f"当前年龄说成{said}岁，与引擎虚岁{nominal}不符")

    return violations


class _GanzhiStreamFilter:
    """流式净化：把命盘里出现过的干支（后台标记）从模型输出里剔掉，防止泄漏给用户。

    干支泄漏是 eval 三大系统 bug 之一：prompt 三令五申「不报干支」仍压不住
    （8 条命例 4 条漏）。check_grounding 只能事后记录，而回答是流式的、已经吐给
    用户。这里在流上边吐边剔，作为确定性兜底。

    只剔『这盘实际存在的干支串』——精确、几乎零误伤：一个命理干支（如壬寅）出现在
    咨询正文里，必是照抄后台标记。干支恒为两字；跨 chunk 分割时最多缓存一个待定的
    天干字（可能是下一个 chunk 才补齐地支的干支头）。check_grounding 仍对**原始**
    输出打分，保留「模型本身是否还在泄漏」的回归信号（净化是给用户的护栏，不是给
    模型的免罪）。"""

    def __init__(self, chart_ganzhi: set[str]):
        self._stems = {g[0] for g in chart_ganzhi}
        self._re = (re.compile("|".join(re.escape(g) for g in chart_ganzhi))
                    if chart_ganzhi else None)
        self._pending = ""
        self.removed = 0

    def feed(self, chunk: str) -> str:
        buf = self._pending + chunk
        self._pending = ""
        if buf and buf[-1] in self._stems:
            self._pending = buf[-1]          # 可能是跨 chunk 干支的天干，先扣住
            buf = buf[:-1]
        return self._strip(buf)

    def flush(self) -> str:
        tail, self._pending = self._pending, ""
        return self._strip(tail)

    def _strip(self, s: str) -> str:
        if not self._re or not s:
            return s

        def _drop(_m):
            self.removed += 1
            return ""

        return self._re.sub(_drop, s)


def build_missing_info_reply(topic: Topic | None, birth_info: BirthInfo) -> tuple[str, ChatState]:
    missing = birth_info.complete_missing_fields()
    topic_text = topic_cn(topic)
    if len(missing) >= 3:
        reply = (
            f"可以，我先按{topic_text}方向帮你看。为了分析，需要确认四个信息："
            "出生年月日、出生时间、出生地、性别。你可以直接一句话告诉我。"
        )
    else:
        fields = "、".join(_FIELD_CN.get(f, f) for f in missing)
        reply = f"还差{fields}。补充后我就可以继续分析。"
        if "birth_time" in missing:
            reply += "出生时间大概几点也可以，比如“早上八点左右”。"

    return reply, ChatState(
        topic=topic,
        needs_more_info=True,
        missing_fields=missing,
        suggested_followups=[],
    )


def build_smalltalk_reply(
    birth_complete: bool = False,
    topic: Topic | None = None,
) -> tuple[str, ChatState]:
    """Friendly reply for greetings / chit-chat — no chart casting.

    State-aware: mid-consultation (birth info already on file) the reply must
    not re-introduce itself or ask for birth info again — that reads as amnesia
    (攻击评测 flip-sympathy 暴露的体验缺陷)。
    """
    if birth_complete:
        reply = (
            "我在。你的出生信息我都记着，不用再报一遍——想继续看哪方面，"
            "直接问就行，事业、感情、财运、性格都可以。"
        )
        return reply, ChatState(
            topic=topic,
            needs_more_info=False,
            missing_fields=[],
            suggested_followups=_followups(topic, None),
        )
    reply = (
        "你好。我可以帮你结合命理看事业、感情、财运和性格的走向。"
        "把出生年月日、出生时间、出生地和性别告诉我，再说说想了解什么，我们就可以开始。"
    )
    return reply, ChatState(
        topic=None,
        needs_more_info=False,
        missing_fields=[],
        suggested_followups=["看看我的事业方向", "我的性格优势是什么？"],
    )


def build_out_of_scope_reply() -> tuple[str, ChatState]:
    """Polite redirect for requests outside the product's scope."""
    reply = (
        "这个问题超出了我能帮你看的范围。我专注于结合命理给事业、感情、财运、性格方面的分析参考，"
        "不提供医疗、投资指令或其它专业建议。如果你愿意，可以从这几个方向问我。"
    )
    return reply, ChatState(
        topic=None,
        needs_more_info=False,
        missing_fields=[],
        suggested_followups=["事业方向怎么选？", "我的性格优势是什么？"],
    )


# Answer-tone presets. These change ONLY the wording style — never the
# structured judgment, the boundaries, or the constraints below. Unknown /
# None falls back to the restrained default (per PRODUCT.md brand).
def stream_consultation_reply(
    topic: Topic | None,
    tool_result: dict[str, Any],
    *,
    source_basis: dict[str, Any],
    clarify_previous: bool = False,
    user_message: str = "",
    history: list[dict[str, Any]] | None = None,
    memory_notes: list[dict[str, Any]] | None = None,
    profile: UserProfile | None = None,
    tone: str | None = None,
    trace_sink=None,
) -> Iterator[tuple[str, ChatState | None, dict[str, Any] | None]]:
    """Stream the consultation reply chunk by chunk.

    Yields tuples of (text_chunk, final_state, generation_trace).
    - During streaming: (chunk, None, None)
    - On completion: ("", chat_state, generation_trace)
    - On LLM unavailable: falls back to non-streaming template reply
    """
    actual_topic = topic or "personality"
    chart = tool_result["chart"]
    diagnosis = tool_result["diagnosis"]
    arbitration = tool_result["arbitration"]
    context = _context_from_tool_result(chart, diagnosis, arbitration, source_basis)
    context["timeline"] = tool_result.get("timeline")

    if not is_configured():
        if clarify_previous:
            reply = _clarify_reply(context)
        elif actual_topic == "career":
            reply = _career_reply(context)
        elif actual_topic == "relationship":
            reply = _relationship_reply(context)
        elif actual_topic == "wealth":
            reply = _wealth_reply(context)
        else:
            reply = _personality_reply(context)
        state = ChatState(topic=actual_topic, needs_more_info=False, missing_fields=[],
                          suggested_followups=_followups(actual_topic, history))
        generation_trace = {"mode": "deterministic_template", "topic": actual_topic}
        yield reply, state, generation_trace
        return

    prompt = _build_stream_reply_prompt(actual_topic, context,
                                         clarify_previous=clarify_previous,
                                         user_message=user_message,
                                         history=history,
                                         memory_notes=memory_notes,
                                         profile=profile,
                                         tone=tone)
    # 只剔『这盘实际出现过的干支』——直接从 prompt 正文(含命盘 JSON)扫出精确集合，
    # 就是模型唯一可能照抄的那些后台标记。
    gz_filter = _GanzhiStreamFilter(set(_GANZHI_RE.findall(prompt["user_prompt"])))
    collected = []   # 原始模型输出(供 grounding 信号)
    shown = []       # 净化后输出(用户实际所见 / 落库)
    try:
        for chunk in stream(prompt["system_prompt"], prompt["user_prompt"],
                                      temperature=0.7, timeout=120,
                                      trace_sink=trace_sink):
            collected.append(chunk)
            clean = gz_filter.feed(chunk)
            if clean:
                shown.append(clean)
                yield clean, None, None
    except LLMError:
        # fallback to template on stream error
        if clarify_previous:
            reply = _clarify_reply(context)
        elif actual_topic == "career":
            reply = _career_reply(context)
        else:
            reply = _personality_reply(context)
        state = ChatState(topic=actual_topic, needs_more_info=False, missing_fields=[],
                          suggested_followups=_followups(actual_topic, history))
        yield reply, state, {"mode": "deterministic_template_fallback", "topic": actual_topic}
        return

    tail = gz_filter.flush()
    if tail:
        shown.append(tail)
        yield tail, None, None

    full_reply = "".join(collected)        # 原始:含可能泄漏的干支
    clean_reply = "".join(shown)           # 净化:用户所见、落库、供 judge/追问
    # grounding 仍打在原始输出上——净化是护栏,不掩盖『模型本身还在泄漏』这个事实。
    grounding_violations = check_grounding(full_reply, context)
    reflection = reflect_on_reply(actual_topic, history, clean_reply,
                                  user_message=user_message,
                                  known_memories=_memory_texts(memory_notes),
                                  trace_sink=trace_sink)
    followups = reflection["followups"]
    state = ChatState(topic=actual_topic, needs_more_info=False,
                     missing_fields=[], suggested_followups=followups)
    generation_trace = {"mode": "deepseek_stream", "topic": actual_topic,
                        "reply": clean_reply, "raw_response": full_reply,
                        "followups": followups, "conclusion": reflection["conclusion"],
                        "memory": reflection["memory"],
                        "grounding_violations": grounding_violations,
                        "sanitized_ganzhi_count": gz_filter.removed}
    yield "", state, generation_trace


# ── Rich static facts for the prompt (depth: 宫位 / 五行流向 / 大运走向) ──
_POS_LABEL = {
    "year": "年柱·根基早年祖上",
    "month": "月柱·格局事业父母",
    "day": "日柱·自身配偶",
    "hour": "时柱·子女晚年下属",
}
_INTERACTION_KEYS = ("gan_he", "san_he", "ban_he", "san_hui", "ban_hui", "chong", "xing", "hai")


def _ten_god_class(dm_el: str, el: str) -> str:
    """An element's 十神 category relative to the 日主 element (so 五行 = 十神)."""
    if el == dm_el:
        return "比劫"
    if ELEMENT_PRODUCTION.get(dm_el) == el:
        return "食伤"
    if ELEMENT_CONQUEST.get(dm_el) == el:
        return "财"
    if ELEMENT_CONQUEST.get(el) == dm_el:
        return "官杀"
    return "印"


def _four_pillars_view(chart: dict[str, Any]) -> dict[str, str]:
    """四柱十神，按宫位标注——让 LLM 知道谁透干、星落哪宫。"""
    fp = chart.get("four_pillars", {})
    out: dict[str, str] = {}
    for pos in ("year", "month", "day", "hour"):
        p = fp.get(pos) or {}
        stem = p.get("stem", {})
        branch = p.get("branch", {})
        out[_POS_LABEL[pos]] = (
            f"{p.get('stem_branch')}（天干{stem.get('char')}={stem.get('ten_god')}，"
            f"地支{branch.get('char')}本气={branch.get('ten_god')}）"
        )
    return out


def _wuxing_view(chart: dict[str, Any]) -> dict[str, str]:
    """五行力量分布，每行标其十神类——给 LLM 推「气的流向 × 十神」。"""
    dist = chart.get("element_distribution") or {}
    dm_el = chart.get("day_master_element")
    out: dict[str, str] = {}
    for el in ("木", "火", "土", "金", "水"):
        d = dist.get(el) or {}
        cls = _ten_god_class(dm_el, el) if dm_el else ""
        out[f"{el}（{cls}）"] = f"{d.get('percentage', 0)}%"
    return out


def _natal_interactions_view(diagnosis: dict[str, Any]) -> list[str]:
    """命局四柱之间的刑冲合会。"""
    inter = diagnosis.get("interactions") or {}
    out: list[str] = []
    for k in _INTERACTION_KEYS:
        for i in inter.get(k, []):
            note = i.get("note") or i.get("kind")
            if note:
                out.append(note)
    return out


def _luck_sequence_view(chart: dict[str, Any]) -> list[str]:
    """大运整条序列（干支 + 起止公历年 + 十神）——人生阶段走向，用公历年表达时段。

    刻意**不带起止虚岁**：那是模型反复把"大运起止岁数"误当成"当事人当前年龄"的诱饵
    （grounding bug）。全盘唯一的年龄只留 current_period.当前虚岁。大运时段用年份说，
    也更合"流年粒度优先"的产品定位。"""
    out: list[str] = []
    for lp in (chart.get("luck") or {}).get("pillars", []):
        out.append(
            f"{lp.get('stem_branch')}（{lp.get('start_year')}-{lp.get('end_year')}年，"
            f"{lp.get('stem_ten_god')}/{lp.get('branch_ten_god')}）"
        )
    return out


def _context_from_tool_result(
    chart: dict[str, Any],
    diagnosis: dict[str, Any],
    arbitration: dict[str, Any],
    source_basis: dict[str, Any],
) -> dict[str, Any]:
    yong = diagnosis.get("yong_shen", {})
    ge = diagnosis.get("ge_ju", {})
    cheng = diagnosis.get("cheng_bai", {})
    strength = chart.get("strength", {})
    cases = arbitration.get("cases", [])
    responses = arbitration.get("responses", {})
    summary = arbitration.get("summary", {})

    arbitration_decisions = {}
    for case_id, resp in responses.items():
        if resp.get("decision") != "无法判定":
            arbitration_decisions[case_id] = {
                "decision": resp["decision"],
                "confidence": resp.get("confidence", 0.0),
                "reasoning": resp.get("reasoning", ""),
            }

    has_unresolved = summary.get("unresolved", 0) > 0

    return {
        "day_master": chart.get("day_master"),
        "day_master_element": chart.get("day_master_element"),
        "strength_verdict": strength.get("verdict"),
        "ge_ju": ge.get("name"),
        "yong_shen_ten_god": yong.get("ten_god"),
        "cheng_bai": cheng.get("verdict"),
        "has_unresolved_cases": has_unresolved,
        "arbitration_decisions": arbitration_decisions,
        # Rich static facts so the model can reason specifically, not generically.
        "four_pillars": _four_pillars_view(chart),
        "wuxing": _wuxing_view(chart),
        "natal_interactions": _natal_interactions_view(diagnosis),
        "luck_sequence": _luck_sequence_view(chart),
        # Current 大运/流年 resolved at cast time — the shared "now" for any
        # time-sensitive part of the answer. May be None for charts cast
        # without a reference_year.
        "current_period": chart.get("current_period"),
        "source_basis": source_basis,
    }


def _career_reply(ctx: dict[str, Any]) -> str:
    prefix = _conservative_prefix(ctx)
    pressure = _pressure_phrase(ctx)
    return (
        f"{prefix}你不是完全不适合创业，但更适合“有专业壁垒、能控制节奏的小步创业”。"
        "如果一开始就做高杠杆、强扩张、强销售的项目，压力会被放大。\n\n"
        f"从命盘结构看，{pressure}，比较适合在规则明确、目标清楚、有挑战的环境里建立信用。"
        "如果走职业路线，适合承担复杂任务、专业负责人、项目统筹这类位置。\n\n"
        "风险在于节奏过急、责任压身，或合伙边界不清。建议先验证现金流和客户来源，再扩大投入。"
    )


def _relationship_reply(ctx: dict[str, Any]) -> str:
    prefix = _conservative_prefix(ctx)
    return (
        f"{prefix}感情上你更需要稳定、清楚、可沟通的关系，不太适合长期处在模糊和拉扯里。\n\n"
        "你的命盘里责任感和自我要求感比较明显，亲密关系里容易想把事情处理好，"
        "但压力大时也可能显得紧、急，或者不太愿意示弱。\n\n"
        "比较适合的相处方式是：边界清楚、承诺明确、遇到问题能直接沟通。"
        "需要注意的是，不要把事业压力带进关系，也不要用控制感代替安全感。"
    )


def _wealth_reply(ctx: dict[str, Any]) -> str:
    prefix = _conservative_prefix(ctx)
    return (
        f"{prefix}财务上更适合靠专业能力、长期信用和稳定现金流积累，不适合一开始追求高波动收益。\n\n"
        "从结构上看，你适合把钱建立在明确的能力、规则和项目交付上。"
        "如果做副业或投资，最好先看可验证的回报周期，而不是只看机会想象。\n\n"
        "风险点是压力上来时容易想快速突破。建议保留安全垫，合作前把分工、退出和账目规则写清楚。"
    )


def _personality_reply(ctx: dict[str, Any]) -> str:
    prefix = _conservative_prefix(ctx)
    pressure = _pressure_phrase(ctx)
    return (
        f"{prefix}你的核心优势在于能扛事、重结果，也比较适合面对有标准、有难度的任务。\n\n"
        f"命盘里{pressure}，所以你在顺的时候执行力强，在压力下也容易被目标推着走。"
        "这会带来专业感和责任感，但也可能让自己长期绷紧。\n\n"
        "成长重点是把责任拆小，把节奏放稳；不要什么都自己扛，学会用流程和边界分担压力。"
    )


def _clarify_reply(ctx: dict[str, Any]) -> str:
    ge_ju = ctx.get("ge_ju")
    if ge_ju in (None, "", "未定"):
        structure_text = "这盘的格局不宜简单下死结论，所以我会结合用神、强弱和成败状态保守判断"
    else:
        structure_text = f"这盘的结构重点在“{ge_ju}”和成败状态"
    return (
        "我主要是按既定的格局和用神逻辑来判断，不是单看某一个字。"
        f"{structure_text}，再结合日主强弱来看，所以结论会偏向责任、压力、节奏和边界这些关键词。\n\n"
        "如果要看完整规则链，后台 trace 里会保留具体诊断、规则引用和仲裁记录。"
    )


def _pressure_phrase(ctx: dict[str, Any]) -> str:
    ge_ju = ctx.get("ge_ju")
    ten_god = ctx.get("yong_shen_ten_god")
    if ge_ju in (None, "", "未定"):
        ge_ju = None
    if ten_god in ("比肩", "劫财"):
        return "自我驱动力和竞争意识比较突出，做事会比较重自主权和掌控感"
    if ge_ju and ten_god:
        return f"{ge_ju}和{ten_god}的信号比较突出，事业压力感和竞争感会比较明显"
    if ge_ju:
        return f"{ge_ju}的信号比较突出，做事会比较重目标和责任"
    return "事业压力感和责任感比较明显"


def _conservative_prefix(ctx: dict[str, Any]) -> str:
    if ctx.get("has_unresolved_cases"):
        return "这里有判断点不宜说得太满，我会把结论说得保守一些。"
    return ""


def _asked_questions(history: list[dict[str, Any]] | None) -> set[str]:
    if not history:
        return set()
    return {str(m.get("content", "")).strip() for m in history if m.get("role") == "user"}


def _followups(
    topic: Topic | None,
    history: list[dict[str, Any]] | None = None,
    *,
    count: int = 3,
) -> list[str]:
    """History-aware fallback follow-ups: drop already-asked, rotate per turn."""
    pool = list(topic_spec(topic).followups)
    asked = _asked_questions(history)
    fresh = [q for q in pool if q not in asked]
    candidates = fresh if len(fresh) >= count else pool
    turns = sum(1 for m in (history or []) if m.get("role") == "assistant")
    start = (turns * count) % len(candidates)
    rotated = candidates[start:] + candidates[:start]
    return rotated[:count]


def _memory_texts(memory_notes: list[dict[str, Any]] | None) -> list[str]:
    """从笔记里抽出非空的 agent 记忆条目(新→旧),喂给 reflect 做去重参照。"""
    if not memory_notes:
        return []
    return [str(n.get("memory_text") or "").strip()
            for n in memory_notes if str(n.get("memory_text") or "").strip()]


def reflect_on_reply(
    topic: Topic | None,
    history: list[dict[str, Any]] | None,
    reply: str,
    *,
    user_message: str = "",
    count: int = 3,
    known_memories: list[str] | None = None,
    trace_sink=None,
) -> dict[str, Any]:
    """One LLM call after the reply: follow-ups + conclusion + memory.

    Returns {"followups": [...], "conclusion": "...", "memory": "..."}.
    Follow-ups fall back to the history-aware pool; conclusion/memory fall back
    to "" when no LLM / on error.

    memory 是 agent 自主记忆:模型自行判断这轮有没有「值得长期记住的用户信息」
    (用户明确说出的处境/计划/事实),没有就空。与 conclusion 互补——conclusion
    记「我们说了什么结论」,memory 记「用户是个什么情况」。

    known_memories:已经记住的记忆条目。不传的话模型看不到记过什么,用户每轮
    重复同一处境就会每轮重复记录,挤占渲染预算——传进来让它只记「新增」。
    """
    result: dict[str, Any] = {
        "followups": _followups(topic, history, count=count),
        "conclusion": "",
        "memory": "",
    }
    if not is_configured():
        return result

    system_prompt = (
        "用户刚问了一个命理咨询问题并得到了回答。基于这段对话，输出严格 JSON，包含三个字段：\n"
        f"1. followups：用户接下来最可能继续问的 {count} 个问题（字符串数组）。"
        "必须是下一步的问题、不复述「当前问题」、不与「已经问过的」重复、与回答方向一致、"
        "用日常口语不带命理术语，每个不超过15字。\n"
        "2. conclusion：一句话（不超过40字）概括这次给用户的核心结论，"
        "供以后回访时参考，口语化、具体、不带术语。\n"
        "3. memory：这轮对话里值得长期记住的用户具体信息（不超过60字），"
        "只记用户明确说出的处境/计划/事实（如「35岁想从运营转产品」「明年打算要孩子」）。"
        "铁律：用户没明说的不记；不记命理术语和干支；"
        "「已记住的信息」里已有的**不要重复记**，只记新增或明确变化的；"
        "本轮没有新信息就给空字符串——宁可空白，绝不臆测。\n"
        '形如 {"followups":["问题一","问题二"],"conclusion":"……","memory":"……"}。只输出 JSON。'
    )
    user_prompt = json.dumps(
        {
            "topic": topic,
            "当前问题": user_message,
            "回答": reply,
            "近期对话": render_history(history),
            "已经问过的": sorted(_asked_questions(history)),
            "已记住的信息": known_memories or [],
        },
        ensure_ascii=False,
    )
    try:
        # 收紧超时、不重试:这是回复送达后的锦上添花(追问/结论/记忆),
        # 前端要等它才能收到 done——宁可放弃这轮增强,不可拖住流的收尾。
        data = json.loads(complete(system_prompt, user_prompt, temperature=0.6,
                                   provider=fast_provider(),  # follow-ups → cheap model
                                   timeout=15, retries=0,
                                   trace_sink=trace_sink))
        if isinstance(data, dict):
            fups = data.get("followups")
            if isinstance(fups, list):
                items = [str(x).strip() for x in fups if str(x).strip()][:count]
                if items:
                    result["followups"] = items
            conclusion = data.get("conclusion")
            if isinstance(conclusion, str) and conclusion.strip():
                result["conclusion"] = conclusion.strip()
            memory = data.get("memory")
            if isinstance(memory, str) and memory.strip():
                # 确定性兜底:prompt 已禁,但干支绝不入库(remove the bait——
                # 记忆会渲染回后续 prompt,带干支等于把诱饵重新放回去)。
                result["memory"] = _GANZHI_RE.sub("", memory.strip())
    except (LLMError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        pass
    return result


def _summarize_current_period(cp: dict[str, Any] | None) -> dict[str, Any] | None:
    """Compact view of the current 大运/流年 for the prompt — the engine's
    deterministic *facts* (十神 roles + 刑冲合会). The model weighs 顺逆 itself."""
    if not cp:
        return None
    lp = cp.get("luck_pillar")
    summary: dict[str, Any] = {
        "公历年": cp.get("year"),
        "当前虚岁（当事人现在多大）": cp.get("nominal_age"),
    }
    # Deliberately NOT exposing the 大运 虚岁 span here. The model kept grabbing
    # its endpoints (e.g. 29 / 38) as the person's CURRENT age — a temp-sensitive
    # grounding bug a prompt rule couldn't reliably suppress. The 大运 time window
    # already lives in 大运走向; current_period needs only "now". Remove the bait.
    if not lp and cp.get("status"):
        summary["当前大运"] = "尚未起运" if cp.get("status") == "pre_luck" else "超出推算范围"

    luck_facts = _facts_view(cp.get("luck_facts"))
    if luck_facts:
        summary["当前大运·事实"] = luck_facts
    liunian_facts = _facts_view(cp.get("liunian_facts"))
    if liunian_facts:
        summary["今年流年·事实"] = liunian_facts
    return summary


def _facts_view(f: dict[str, Any] | None) -> dict[str, Any] | None:
    """The engine's deterministic facts for a 大运/流年 — 十神角色 + 与命局/大运的
    刑冲合会关系。No 吉凶 verdict: the model weighs these into 顺逆 itself."""
    if not f:
        return None

    def role(r: dict[str, Any] | None) -> str | None:
        if not r:
            return None
        meaning = ROLE_PLAIN.get(r.get("role"), r.get("role"))
        return f"{r.get('char')}（{r.get('ten_god')}，{meaning}）"

    view: dict[str, Any] = {"干支": f.get("pillar"), "天干": role(f.get("stem"))}
    if f.get("branch"):
        view["地支本气"] = role(f.get("branch"))
    relations = f.get("relations") or []
    if relations:
        view["与命局/大运的关系"] = relations
    if f.get("yong_unknown"):
        view["说明"] = "用神未定，喜忌待判"
    return view


def _build_analysis_block(context: dict[str, Any]) -> dict[str, Any]:
    """命盘事实块——刻意**不含**逐轮易变字段（topic / clarify_previous / 用户问题）。

    这样同一命盘（+同一参考年）下，这块大 JSON 在每一轮都**字节一致**，构成稳定
    前缀，让 DeepSeek 的自动前缀缓存命中（命中部分约 1/10 计费），而不是每轮把整张
    命盘重新计费一遍。易变的信号（看哪个方向、是不是追问）放到末尾「用户当前的问题」段。
    """
    block = {
        "day_master": context.get("day_master"),
        "day_master_element": context.get("day_master_element"),
        "strength_verdict": context.get("strength_verdict"),
        "ge_ju": context.get("ge_ju"),
        "yong_shen_ten_god": context.get("yong_shen_ten_god"),
        "cheng_bai": context.get("cheng_bai"),
        "has_unresolved_cases": context.get("has_unresolved_cases"),
        "arbitration_decisions": context.get("arbitration_decisions", {}),
        "四柱十神(按宫位)": context.get("four_pillars"),
        "五行力量(标十神类)": context.get("wuxing"),
        "大运走向(整条)": context.get("luck_sequence"),
    }
    natal = context.get("natal_interactions")
    if natal:
        block["命局刑冲合会"] = natal
    timeline = context.get("timeline")
    if timeline:
        block["关键年份·流年透视"] = timeline
    current_period = _summarize_current_period(context.get("current_period"))
    if current_period is not None:
        block["current_period"] = current_period
    return block


def _build_stream_reply_prompt(
    topic: Topic,
    context: dict[str, Any],
    *,
    clarify_previous: bool,
    user_message: str = "",
    history: list[dict[str, Any]] | None = None,
    memory_notes: list[dict[str, Any]] | None = None,
    profile: UserProfile | None = None,
    tone: str | None = None,
) -> dict[str, str]:
    """Streaming (non-JSON) prompt that answers the user's current question.

    拼装逻辑已移入 prompt_registry(段注册表 + 三区拼装器):段的内容、
    顺序、挂载条件都是注册表数据;稳定前缀/易变尾部/反注入位置三条铁律
    由 registry 的类型与结构强制。此处只负责组 ctx。
    """
    ctx = build_turn_ctx(
        topic,
        analysis_json=json.dumps(_build_analysis_block(context),
                                 ensure_ascii=False, indent=2),
        clarify_previous=clarify_previous,
        user_message=user_message,
        history=history,
        memory_notes=memory_notes,
        profile=profile,
        tone=tone,
    )
    return compose(ctx)
