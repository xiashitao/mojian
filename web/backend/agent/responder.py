"""User-facing response generation for the MVP chat agent."""
from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from ..config import settings
from ..services.deepseek import DeepSeekAPIError, call_deepseek, stream_deepseek
from .models import BirthInfo, ChatState, Topic


_FIELD_CN = {
    "birth_date": "出生年月日",
    "birth_time": "出生时间",
    "birth_place": "出生地",
    "gender": "性别",
}


def build_missing_info_reply(topic: Topic | None, birth_info: BirthInfo) -> tuple[str, ChatState]:
    missing = birth_info.complete_missing_fields()
    topic_text = _topic_cn(topic)
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


def build_consultation_reply(
    topic: Topic | None,
    tool_result: dict[str, Any],
    *,
    source_basis: dict[str, Any],
    clarify_previous: bool = False,
    user_message: str = "",
    history: list[dict[str, Any]] | None = None,
) -> tuple[str, ChatState, dict[str, Any]]:
    actual_topic = topic or "personality"
    chart = tool_result["chart"]
    diagnosis = tool_result["diagnosis"]
    arbitration = tool_result["arbitration"]
    context = _context_from_tool_result(chart, diagnosis, arbitration, source_basis)

    followups = _followups(actual_topic, history)
    prompt = _build_reply_prompt(
        actual_topic,
        context,
        clarify_previous=clarify_previous,
        followups=followups,
        user_message=user_message,
        history=history,
    )
    llm_result = _call_reply_llm(prompt)
    if llm_result is not None:
        reply = llm_result["reply"]
        if llm_result.get("suggested_followups"):
            followups = [str(item) for item in llm_result["suggested_followups"][:3]]
    else:
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
        if followups:
            reply += "\n\n你可以继续问：" + " / ".join(followups)

    state = ChatState(
        topic=actual_topic,
        needs_more_info=False,
        missing_fields=[],
        suggested_followups=followups,
    )
    generation_trace = {
        "mode": "deepseek" if llm_result is not None else "deterministic_template",
        "topic": actual_topic,
        "source_basis": source_basis,
        "context": context,
        "reply": reply,
        "raw_response": llm_result["raw_response"] if llm_result is not None else None,
    }
    return reply, state, generation_trace


def stream_consultation_reply(
    topic: Topic | None,
    tool_result: dict[str, Any],
    *,
    source_basis: dict[str, Any],
    clarify_previous: bool = False,
    user_message: str = "",
    history: list[dict[str, Any]] | None = None,
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

    if not settings.deepseek_api_key:
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
                                         history=history)
    collected = []
    try:
        for chunk in stream_deepseek(prompt["system_prompt"], prompt["user_prompt"],
                                      temperature=0.7):
            collected.append(chunk)
            yield chunk, None, None
    except DeepSeekAPIError:
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
    followups = generate_followups(actual_topic, context, history, full_reply,
                                   user_message=user_message)
    state = ChatState(topic=actual_topic, needs_more_info=False,
                     missing_fields=[], suggested_followups=followups)
    generation_trace = {"mode": "deepseek_stream", "topic": actual_topic,
                        "reply": full_reply, "raw_response": full_reply,
                        "followups": followups}
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


def generate_followups(
    topic: Topic | None,
    context: dict[str, Any],
    history: list[dict[str, Any]] | None,
    reply: str,
    *,
    user_message: str = "",
    count: int = 3,
) -> list[str]:
    """LLM-generated follow-ups grounded in the current Q&A + session history.

    Falls back to the history-aware pool when no LLM is configured or on error.
    """
    fallback = _followups(topic, history, count=count)
    if not settings.deepseek_api_key:
        return fallback

    system_prompt = (
        "用户刚问了一个命理咨询问题并得到了回答。请基于这段对话，"
        f"提出用户接下来最可能继续问的 {count} 个问题。严格遵守：\n"
        "1. 必须是「下一步」的问题：在回答基础上深入某一点，或转向相关但全新的角度；\n"
        "2. 绝对不要复述或改写「当前问题」，也不要与「已经问过的」重复或近义；\n"
        "3. 要与「回答」的建议方向一致，不要建议回答里明确不推荐的做法；\n"
        "4. 用日常口语，不要出现命理术语、古籍或流派名（如偏财格、财星救应、用神这类都不要）；\n"
        "5. 每个不超过15字，具体、彼此不同，不要序号或引号前缀；\n"
        '6. 只输出 JSON 字符串数组，例如 ["问题一","问题二"]。'
    )
    user_prompt = json.dumps(
        {
            "topic": topic,
            "当前问题": user_message,
            "回答": reply,
            "近期对话": _render_history(history),
            "已经问过的": sorted(_asked_questions(history)),
        },
        ensure_ascii=False,
    )
    try:
        raw = call_deepseek(system_prompt, user_prompt, temperature=0.6)
        data = json.loads(raw)
        if isinstance(data, dict):
            data = next((v for v in data.values() if isinstance(v, list)), [])
        items = [str(x).strip() for x in data if str(x).strip()]
        return items[:count] or fallback
    except (DeepSeekAPIError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return fallback


def _topic_cn(topic: Topic | None) -> str:
    return {
        "career": "事业",
        "relationship": "感情",
        "wealth": "财务",
        "personality": "性格",
    }.get(topic or "career", "这个问题")


def _render_history(history: list[dict[str, Any]] | None, *, max_turns: int = 4) -> str:
    """Compact transcript of the most recent turns for follow-up context."""
    if not history:
        return ""
    role_cn = {"user": "用户", "assistant": "助手"}
    lines: list[str] = []
    for msg in history[-max_turns:]:
        content = str(msg.get("content", "")).strip()
        if not content:
            continue
        if len(content) > 180:
            content = content[:180] + "…"
        role = role_cn.get(str(msg.get("role")), str(msg.get("role")))
        lines.append(f"{role}：{content}")
    return "\n".join(lines)


def _build_analysis_block(topic: Topic, context: dict[str, Any], *, clarify_previous: bool) -> dict[str, Any]:
    return {
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


def _build_stream_reply_prompt(
    topic: Topic,
    context: dict[str, Any],
    *,
    clarify_previous: bool,
    user_message: str = "",
    history: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    """Streaming (non-JSON) prompt that answers the user's current question."""
    system_prompt = (
        "你是一位谨慎、专业的命理咨询助手。"
        "请直接、充分地回答「用户当前的问题」，回答必须基于下方结构化分析结果，"
        "不要编造超出分析结论的内容，也不要重复之前已经说过的话。"
        "不要提及具体流派名、古籍或后台规则，也不要堆砌命理术语。"
        "用日常语言展开，依次涵盖：直接结论、适配的条件或方向、需要注意的风险、一条可执行的建议。"
        "篇幅约300–500字，分2–4个自然段，语气沉稳克制。不要在结尾附上追问建议。"
    )
    analysis_block = _build_analysis_block(topic, context, clarify_previous=clarify_previous)

    parts = [
        "## 结构化分析结果",
        json.dumps(analysis_block, ensure_ascii=False, indent=2),
    ]
    transcript = _render_history(history)
    if transcript:
        parts.append("## 最近的对话")
        parts.append(transcript)
    parts.append("## 用户当前的问题")
    parts.append(user_message.strip() or f"请就「{_topic_cn(topic)}」方向给我分析。")

    return {"system_prompt": system_prompt, "user_prompt": "\n\n".join(parts)}


def _build_reply_prompt(
    topic: Topic,
    context: dict[str, Any],
    *,
    clarify_previous: bool,
    followups: list[str],
    user_message: str = "",
    history: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    system_prompt = (
        "你是一位谨慎、专业、简洁的命理咨询助手。"
        "请直接回答 user_question，回答必须基于结构化分析结果，"
        "不要编造超出证据的结论，也不要重复 recent_dialog 里已经说过的话。"
        "用户回复中不要出现具体流派名、古籍书名或后台规则来源。"
        "输出必须是严格 JSON，不要输出任何额外文本。"
    )
    user_payload = {
        "topic": topic,
        "clarify_previous": clarify_previous,
        "user_question": user_message.strip(),
        "recent_dialog": _render_history(history),
        "analysis": _build_analysis_block(topic, context, clarify_previous=clarify_previous),
        "response_policy": {
            "tone": "consultation",
            "avoid_raw_rule_dumps": True,
            "mention_technical_terms_sparingly": True,
            "focus": "answer user_question with user-facing advice",
        },
        "required_fields": ["reply", "suggested_followups"],
        "followup_candidates": followups,
    }
    user_prompt = json.dumps(user_payload, ensure_ascii=False, indent=2)
    return {"system_prompt": system_prompt, "user_prompt": user_prompt}


def _call_reply_llm(prompt: dict[str, str]) -> dict[str, Any] | None:
    if not settings.deepseek_api_key:
        return None
    try:
        raw = call_deepseek(
            prompt["system_prompt"],
            prompt["user_prompt"],
            temperature=0.2,
        )
        data = json.loads(raw)
        reply = str(data["reply"]).strip()
        if not reply:
            raise ValueError("empty reply")
        suggested_followups = data.get("suggested_followups", [])
        if not isinstance(suggested_followups, list):
            suggested_followups = []
        return {
            "reply": reply,
            "suggested_followups": suggested_followups,
            "raw_response": raw,
        }
    except (DeepSeekAPIError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None
