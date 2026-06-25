"""User-facing response generation for the MVP chat agent."""
from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from ..services.llm import LLMError, complete, is_configured, stream
from .context import render_history, render_notes, topic_cn
from .models import BirthInfo, ChatState, Topic


_FIELD_CN = {
    "birth_date": "出生年月日",
    "birth_time": "出生时间",
    "birth_place": "出生地",
    "gender": "性别",
}


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


def build_smalltalk_reply() -> tuple[str, ChatState]:
    """Friendly reply for greetings / chit-chat — no chart casting."""
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
DEFAULT_TONE = "advisor"
_TONE_INSTRUCTION = {
    "advisor": "语气沉稳克制，像一位审慎的顾问，给有依据、有边界的参考。",
    "friend": "语气温和亲切，像一个耐心的朋友陪你聊，可以多一点共情，但不夸张、不打包票。",
    "direct": "语气直接利落，先给结论、少铺垫、不绕弯，但仍然保留必要的边界和不确定性。",
}


def _tone_instruction(tone: str | None) -> str:
    return _TONE_INSTRUCTION.get(tone or DEFAULT_TONE, _TONE_INSTRUCTION[DEFAULT_TONE])


def stream_consultation_reply(
    topic: Topic | None,
    tool_result: dict[str, Any],
    *,
    source_basis: dict[str, Any],
    clarify_previous: bool = False,
    user_message: str = "",
    history: list[dict[str, Any]] | None = None,
    memory_notes: list[dict[str, Any]] | None = None,
    tone: str | None = None,
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
                                         tone=tone)
    collected = []
    try:
        for chunk in stream(prompt["system_prompt"], prompt["user_prompt"],
                                      temperature=0.7):
            collected.append(chunk)
            yield chunk, None, None
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

    full_reply = "".join(collected)
    reflection = reflect_on_reply(actual_topic, history, full_reply, user_message=user_message)
    followups = reflection["followups"]
    state = ChatState(topic=actual_topic, needs_more_info=False,
                     missing_fields=[], suggested_followups=followups)
    generation_trace = {"mode": "deepseek_stream", "topic": actual_topic,
                        "reply": full_reply, "raw_response": full_reply,
                        "followups": followups, "conclusion": reflection["conclusion"]}
    yield "", state, generation_trace


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


_FOLLOWUP_POOL: dict[str, list[str]] = {
    "career": ["我适合什么行业？", "适合单干还是合伙？", "现在更适合创业还是上班？",
               "我适合什么样的岗位？", "事业上最该避开什么？", "怎么发挥我的长处？"],
    "relationship": ["我适合怎样的伴侣？", "感情里最需要注意什么？", "我容易遇到什么样的人？",
                     "怎么经营好长期关系？", "我的感情短板在哪？"],
    "wealth": ["我适合靠什么赚钱？", "合作和投资要注意什么？", "我更适合正财还是偏财？",
               "怎么守住已有的财？", "我的财务风险点在哪？"],
    "personality": ["我的优势在哪里？", "压力大的时候怎么调整？", "我的短板是什么？",
                    "我适合怎样的成长方式？", "别人通常怎么看我？"],
}


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
    pool = _FOLLOWUP_POOL.get(topic or "personality", _FOLLOWUP_POOL["personality"])
    asked = _asked_questions(history)
    fresh = [q for q in pool if q not in asked]
    candidates = fresh if len(fresh) >= count else pool
    turns = sum(1 for m in (history or []) if m.get("role") == "assistant")
    start = (turns * count) % len(candidates)
    rotated = candidates[start:] + candidates[:start]
    return rotated[:count]


def reflect_on_reply(
    topic: Topic | None,
    history: list[dict[str, Any]] | None,
    reply: str,
    *,
    user_message: str = "",
    count: int = 3,
) -> dict[str, Any]:
    """One LLM call after the reply: dynamic follow-ups + a one-line conclusion.

    Returns {"followups": [...], "conclusion": "..."}. Follow-ups fall back to
    the history-aware pool; conclusion falls back to "" when no LLM / on error.
    """
    result: dict[str, Any] = {
        "followups": _followups(topic, history, count=count),
        "conclusion": "",
    }
    if not is_configured():
        return result

    system_prompt = (
        "用户刚问了一个命理咨询问题并得到了回答。基于这段对话，输出严格 JSON，包含两个字段：\n"
        f"1. followups：用户接下来最可能继续问的 {count} 个问题（字符串数组）。"
        "必须是下一步的问题、不复述「当前问题」、不与「已经问过的」重复、与回答方向一致、"
        "用日常口语不带命理术语，每个不超过15字。\n"
        "2. conclusion：一句话（不超过40字）概括这次给用户的核心结论，"
        "供以后回访时参考，口语化、具体、不带术语。\n"
        '形如 {"followups":["问题一","问题二"],"conclusion":"……"}。只输出 JSON。'
    )
    user_prompt = json.dumps(
        {
            "topic": topic,
            "当前问题": user_message,
            "回答": reply,
            "近期对话": render_history(history),
            "已经问过的": sorted(_asked_questions(history)),
        },
        ensure_ascii=False,
    )
    try:
        data = json.loads(complete(system_prompt, user_prompt, temperature=0.6))
        if isinstance(data, dict):
            fups = data.get("followups")
            if isinstance(fups, list):
                items = [str(x).strip() for x in fups if str(x).strip()][:count]
                if items:
                    result["followups"] = items
            conclusion = data.get("conclusion")
            if isinstance(conclusion, str) and conclusion.strip():
                result["conclusion"] = conclusion.strip()
    except (LLMError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        pass
    return result


def _summarize_current_period(cp: dict[str, Any] | None) -> dict[str, Any] | None:
    """Compact, grounding-friendly view of the current 大运/流年 for the prompt."""
    if not cp:
        return None
    ln = cp.get("liunian", {})
    lp = cp.get("luck_pillar")
    summary: dict[str, Any] = {
        "公历年": cp.get("year"),
        "虚岁": cp.get("nominal_age"),
        "流年十神": {
            "天干": ln.get("stem_ten_god"),
            "地支": ln.get("branch_ten_god"),
        },
    }
    if lp:
        summary["当前大运十神"] = {
            "天干": lp.get("stem_ten_god"),
            "地支": lp.get("branch_ten_god"),
            "起止年龄": [lp.get("start_age"), lp.get("end_age")],
        }
    else:
        # status == pre_luck / beyond_range
        summary["当前大运"] = "尚未起运" if cp.get("status") == "pre_luck" else "超出推算范围"
    return summary


def _build_analysis_block(topic: Topic, context: dict[str, Any], *, clarify_previous: bool) -> dict[str, Any]:
    block = {
        "topic": topic,
        "clarify_previous": clarify_previous,
        "day_master": context.get("day_master"),
        "day_master_element": context.get("day_master_element"),
        "strength_verdict": context.get("strength_verdict"),
        "ge_ju": context.get("ge_ju"),
        "yong_shen_ten_god": context.get("yong_shen_ten_god"),
        "cheng_bai": context.get("cheng_bai"),
        "has_unresolved_cases": context.get("has_unresolved_cases"),
        "arbitration_decisions": context.get("arbitration_decisions", {}),
    }
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
    tone: str | None = None,
) -> dict[str, str]:
    """Streaming (non-JSON) prompt that answers the user's current question."""
    system_prompt = (
        "你是一位谨慎、专业的命理咨询助手。"
        "请直接、充分地回答「用户当前的问题」，回答必须基于下方结构化分析结果，"
        "不要编造超出分析结论的内容，也不要重复之前已经说过的话。"
        "若有「过往咨询记录」，自然地保持一致、可适当呼应，但不要照搬复述。"
        "分析结果里的 current_period 是用户「当下所处的大运和今年流年」；"
        "当问题涉及近期、今年、当下时机或近几年走势时，要结合它来谈，"
        "但同样用日常语言，不要报出干支或十神这类术语。"
        "不要提及具体流派名、古籍或后台规则，也不要堆砌命理术语。"
        "用日常语言展开，依次涵盖：直接结论、适配的条件或方向、需要注意的风险、一条可执行的建议。"
        "篇幅约300–500字，分2–4个自然段。"
        # Tone affects wording only; all constraints above still hold.
        f"{_tone_instruction(tone)}"
        "不要在结尾附上追问建议。"
    )
    analysis_block = _build_analysis_block(topic, context, clarify_previous=clarify_previous)

    parts = [
        "## 结构化分析结果",
        json.dumps(analysis_block, ensure_ascii=False, indent=2),
    ]
    notes = render_notes(memory_notes, topic)
    if notes:
        parts.append("## 过往咨询记录（这位用户之前聊过的结论）")
        parts.append(notes)
    transcript = render_history(history)
    if transcript:
        parts.append("## 最近的对话")
        parts.append(transcript)
    parts.append("## 用户当前的问题")
    parts.append(user_message.strip() or f"请就「{topic_cn(topic)}」方向给我分析。")

    return {"system_prompt": system_prompt, "user_prompt": "\n\n".join(parts)}
