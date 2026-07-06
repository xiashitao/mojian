"""MVP state machine for the chat agent."""
from __future__ import annotations

import json
import time
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from ..services import llm
from ..config import settings
from . import memory, repository
from .chart_card import build_chart_card
from .profile import build_or_update_profile
from .extractor import merge_birth_info, _has_birth_signal
from .ids import new_analysis_id
from .models import BirthInfo, ChatState, ConversationState, Topic
from .router import route
from .responder import (
    build_missing_info_reply,
    build_out_of_scope_reply,
    build_smalltalk_reply,
    stream_consultation_reply,
)
from .tools import run_bazibase_tools
from .tracing import TraceWriter

from bazibase import solar_ganzhi_year


def _recall_note(bi) -> str:
    """A transparency line when the birth was recalled from memory, so the user
    knows what it's using (and can correct it)."""
    gender = "男" if bi.gender == "male" else "女" if bi.gender == "female" else ""
    info = " · ".join(p for p in (bi.birth_date, bi.birth_place, gender) if p)
    return (
        f"（我先用你之前保存的生辰：{info} 来看；"
        "如需更换，直接把新的生辰发我即可。）\n\n"
    )


def _profile_changed(before, after) -> bool:
    """Whether the profile update actually differs from the current one.
    Avoids needless DB writes (and prompt-cache invalidation downstream) when
    the LLM returned the same profile it was given."""
    if before is None:
        return not after.is_empty()
    return before.model_dump() != after.model_dump()


def stream_chat(message: str, conversation_id: str | None = None, *, user_id: str | None = None, memory_key: str | None = None, subject: str | None = None, tone: str | None = None) -> Iterator[str]:
    """Stream one user message response as newline-delimited JSON chunks.

    Yields:
        JSON lines of the form:
          {"type": "token", "text": "..."}   — incremental reply text
          {"type": "chart", "chart": {...}}  — chart card payload (once per birth)
          {"type": "needs_subject_confirmation", "birth_info": {...}}
                                            — birth extracted but subject unclear;
                                              frontend should ask "这是哪位的?"
                                              and resend with subject set
          {"type": "done", "conversation_id": ..., "analysis_id": ...,
           "state": {...}}                    — final metadata (last line)
          {"type": "error", "detail": "..."}  — on failure

    `subject`: when set (e.g. from the frontend confirmation dialog), forces
    the conversation's current subject for this turn — used to resolve
    "unknown"-subject births. When None, the conversation's current_subject
    is used (defaulting to "self").
    """
    started = time.monotonic()
    # Own the conversation by the memory key (user id, else anonymous id).
    conversation = repository.ensure_conversation(conversation_id, user_id=memory_key or user_id)
    conv_id = conversation["id"]
    user_message = repository.add_message(conv_id, "user", message)
    analysis_id = _new_unique_analysis_id()
    run = repository.create_agent_run(
        conv_id,
        user_message["id"],
        analysis_id,
        model=llm.active_model() if llm.is_configured() else "deterministic",
    )
    tracer = TraceWriter(run["id"])

    intent: str | None = None
    topic: Topic | None = None
    status = "success"
    error: str | None = None
    assistant_message_id: str | None = None
    reply_parts: list[str] = []
    chat_state = ChatState(topic=None, needs_more_info=False, missing_fields=[], suggested_followups=[])
    chart_card_payload: dict[str, Any] | None = None
    conclusion: str = ""  # one-line takeaway of this turn, stored on the message

    try:
        state = _load_state(conv_id)
        # 主体解析优先级:前端显式传入(确认过的) > 会话上次主体 > 默认 self。
        # 切换主体后,所有记忆(八字/画像/笔记)按新主体隔离重载。
        if subject and subject != state.current_subject:
            state.current_subject = subject
            # 切主体:丢弃旧主体的 birth_info,改从记忆恢复新主体的(若有)。
            state.birth_info = BirthInfo()
        current_subject = state.current_subject

        # Seed remembered birth info (for THIS subject) so returning users skip
        # re-entering it. Note: subject-scoped, not user-scoped.
        remembered = None
        if not state.birth_info.is_complete():
            remembered = memory.get_birth_info(memory_key, current_subject)
            if remembered:
                state.birth_info = merge_birth_info(remembered, state.birth_info)

        decision = route(message, state)
        intent = decision.intent
        topic = decision.topic
        merged_birth_info = decision.birth_info
        tracer.add("extract_input", input_data={"message": message},
                   output_data=decision.model_dump(),
                   summary=f"Routed to action={decision.action}.")

        # 抽到了明确的主体("我儿子的"→child)且与会话当前主体不同 → 切换。
        # 切换后,重新按新主体加载记忆(八字可能完全不同)。
        if decision.subject and decision.subject not in (None, "unknown") \
                and decision.subject != current_subject:
            current_subject = decision.subject
            state.current_subject = current_subject
            # 若用户本轮新报了完整八字,以新八字为准;否则尝试从记忆恢复该主体。
            if merged_birth_info.is_complete():
                state.birth_info = merged_birth_info
            else:
                remembered_other = memory.get_birth_info(memory_key, current_subject)
                state.birth_info = remembered_other or BirthInfo(subject=current_subject)
                merged_birth_info = state.birth_info

        state.birth_info = merged_birth_info
        state.birth_info.subject = current_subject  # 落实 subject 到 birth_info
        state.current_topic = topic or state.current_topic
        state.last_analysis_id = analysis_id
        memory.save_birth_info(memory_key, merged_birth_info, subject=current_subject)
        tracer.add("merge_session_state",
                   input_data={"previous_state": repository.get_conversation_state(conv_id)},
                   output_data=state.model_dump(), summary="Merged session state.")

        # Transparency: if the birth was recalled from memory (the user didn't
        # type it this turn) and it's the first turn, say what we're using.
        birth_recalled = (
            bool(remembered and remembered.is_complete())
            and not _has_birth_signal(message)
        )
        first_turn = len(repository.get_conversation_messages(conv_id)) <= 1
        recall_note = (
            _recall_note(merged_birth_info) if birth_recalled and first_turn else ""
        )

        if decision.action in ("smalltalk", "out_of_scope"):
            reply, chat_state = (
                build_smalltalk_reply()
                if decision.action == "smalltalk"
                else build_out_of_scope_reply()
            )
            yield json.dumps({"type": "token", "text": reply}, ensure_ascii=False) + "\n"
            reply_parts.append(reply)
            tracer.add("generate_reply", input_data={"intent": intent},
                       output_data={"mode": decision.action, "reply": reply},
                       summary=f"Handled {decision.action} without chart casting.")
        elif decision.action == "ask_topic":
            reply, chat_state = _build_topic_question()
            yield json.dumps({"type": "token", "text": reply}, ensure_ascii=False) + "\n"
            reply_parts.append(reply)
        elif decision.action == "ask_birth_info":
            reply, chat_state = build_missing_info_reply(topic, merged_birth_info)
            yield json.dumps({"type": "token", "text": reply}, ensure_ascii=False) + "\n"
            reply_parts.append(reply)
        elif decision.action == "confirm_subject":
            # 八字齐全但「不知道是谁的」:不排盘,发确认事件让前端弹表单。
            # 把已抽到的八字信息一并返回,供前端展示("这套 1990-05-15 的生辰是哪位的?")。
            chat_state = ChatState(
                topic=topic, needs_more_info=True,
                missing_fields=[],
                suggested_followups=[],
            )
            yield json.dumps({
                "type": "needs_subject_confirmation",
                "birth_info": merged_birth_info.model_dump(),
            }, ensure_ascii=False) + "\n"
            tracer.add("confirm_subject",
                       input_data={"subject": decision.subject},
                       output_data={"birth_info": merged_birth_info.model_dump()},
                       summary="Birth complete but subject unclear; asked user to confirm.")
        else:
            # Inject "now" here — the only place the agent reads the clock — so
            # the chart resolves its current 大运 + 流年 as the shared basis for
            # all downstream judgments, while the engine stays clock-free. Use
            # the 立春-based 干支 year (not the calendar year): before 立春 the
            # 流年 still belongs to the previous 干支 year.
            tool_result = run_bazibase_tools(
                merged_birth_info,
                reference_year=solar_ganzhi_year(datetime.now()),
            )
            tracer.add("cast_chart", input_data=merged_birth_info.model_dump(),
                       output_data=tool_result["chart"], summary="Casted Ba Zi chart.")
            tracer.add("diagnose",
                       input_data={"chart_summary": tool_result["chart"].get("chart_summary")},
                       output_data=tool_result["diagnosis"],
                       summary=tool_result.get("diagnosis_summary"))
            arb_summary = tool_result["arbitration"]["summary"]
            tracer.add("prepare_arbitration",
                       input_data={"diagnosis_summary": tool_result.get("diagnosis_summary")},
                       output_data=tool_result["arbitration"],
                       summary=(f"Detected {arb_summary['total']} arbitration cases. "
                                f"Resolved: {arb_summary['resolved']}, "
                                f"Unresolved: {arb_summary['unresolved']}."))

            # Show the chart card once per chart — on the first consult for this
            # birth, or again only if the birth info changed.
            birth_key = "|".join(
                str(v) for v in (
                    merged_birth_info.birth_date, merged_birth_info.birth_time,
                    merged_birth_info.longitude, merged_birth_info.gender,
                )
            )
            if state.chart_shown_for != birth_key:
                chart_card_payload = build_chart_card(
                    tool_result["chart"],
                    merged_birth_info,
                    (tool_result.get("diagnosis") or {}).get("interactions"),
                )
                state.chart_shown_for = birth_key
                yield json.dumps(
                    {"type": "chart", "chart": chart_card_payload},
                    ensure_ascii=False,
                ) + "\n"

            if recall_note:
                reply_parts.append(recall_note)
                yield json.dumps({"type": "token", "text": recall_note}, ensure_ascii=False) + "\n"

            clarify = decision.action == "clarify"
            prior_messages = _prior_messages(conv_id, user_message["id"])
            past_notes = memory.recent_notes(memory_key, subject=current_subject)
            current_profile = memory.get_profile(memory_key, subject=current_subject)
            generation_trace = None
            for chunk, final_state, generation_trace in stream_consultation_reply(
                topic, tool_result,
                source_basis=state.source_basis,
                clarify_previous=clarify,
                user_message=message,
                history=prior_messages,
                memory_notes=past_notes,
                profile=current_profile,
                tone=tone,
            ):
                if chunk:
                    reply_parts.append(chunk)
                    yield json.dumps({"type": "token", "text": chunk}, ensure_ascii=False) + "\n"
                if final_state is not None:
                    chat_state = final_state
                    tracer.add("generate_reply",
                               input_data={"topic": topic, "intent": intent},
                               output_data=generation_trace,
                               summary="Generated consultation reply.")

            # Remember a one-line conclusion of this consultation for next time.
            conclusion = (generation_trace or {}).get("conclusion", "")
            if conclusion:
                memory.add_note(memory_key, topic=topic, question=message,
                                conclusion=conclusion, analysis_id=analysis_id,
                                subject=current_subject)
                tracer.add("update_memory", input_data={"topic": topic},
                           output_data={"conclusion": conclusion},
                           summary="Saved consultation conclusion to user memory.")

            # 用户画像:每 N 轮咨询后用 fast 模型批量更新。
            # 用 turns_since_update 计数,达到阈值就回顾最近的笔记+对话,更新画像。
            # 放在 reply 生成之后,不阻塞用户(回答已经流式返回完了)。
            # 按主体隔离:self 和 child 的画像分别更新,互不污染。
            if settings.profile_enabled:
                turns = memory.increment_profile_turns(memory_key, subject=current_subject)
                if turns >= settings.profile_update_interval:
                    try:
                        current = memory.get_profile(memory_key, subject=current_subject)
                        interval = settings.profile_update_interval
                        recent_notes = memory.recent_notes(memory_key, subject=current_subject, limit=interval)
                        updated = build_or_update_profile(
                            current=current,
                            recent_notes=recent_notes,
                            recent_history=prior_messages,
                        )
                        # 只在画像确实变化时才写库(避免无谓的 DB 写 + 缓存失效)。
                        if _profile_changed(current, updated):
                            memory.save_profile(memory_key, updated, subject=current_subject)
                            tracer.add(
                                "update_profile",
                                input_data={"turns": turns},
                                output_data=updated.model_dump(),
                                summary="Updated user profile from recent consultations.",
                            )
                    except Exception as e:  # 画像失败绝不能影响主流程
                        tracer.add("update_profile_error", input_data={"error": str(e)},
                                   output_data={}, summary=f"Profile update skipped: {e}")

        full_reply = "".join(reply_parts)
        repository.update_conversation_state(conv_id, state.model_dump())
        metadata = chat_state.model_dump()
        if chart_card_payload:
            metadata["chart"] = chart_card_payload  # so the card survives reload
        if conclusion:
            metadata["conclusion"] = conclusion  # so render_history can compress older turns
        assistant_message = repository.add_message(
            conv_id, "assistant", full_reply,
            analysis_id=analysis_id, metadata=metadata,
        )
        assistant_message_id = assistant_message["id"]
        tracer.add("persist_state", input_data={}, output_data=state.model_dump(),
                   summary="Persisted conversation state.")

    except Exception as exc:
        status = "failed"
        error = str(exc)
        err_reply = "分析未能完成，请稍后再试。"
        reply_parts.append(err_reply)
        yield json.dumps({"type": "error", "detail": error}, ensure_ascii=False) + "\n"
        assistant_message = repository.add_message(
            conv_id, "assistant", err_reply,
            analysis_id=analysis_id, metadata=chat_state.model_dump(),
        )
        assistant_message_id = assistant_message["id"]
        tracer.add("error", input_data={"message": message},
                   output_data={"error": error}, summary="Agent run failed.")

    repository.finish_agent_run(
        run["id"],
        assistant_message_id=assistant_message_id,
        status=status, intent=intent, topic=topic,
        started_monotonic=started, error=error,
        metadata={"analysis_id": analysis_id},
    )

    yield json.dumps({
        "type": "done",
        "conversation_id": conv_id,
        "analysis_id": analysis_id,
        "state": chat_state.model_dump(),
    }, ensure_ascii=False) + "\n"


def _load_state(conversation_id: str) -> ConversationState:
    data = repository.get_conversation_state(conversation_id)
    if not data:
        return ConversationState()
    try:
        return ConversationState(**data)
    except Exception:
        return ConversationState()


def _prior_messages(conversation_id: str, current_message_id: str) -> list[dict[str, Any]]:
    """Persisted turns before the current user message (for follow-up context).

    Surfaces each assistant turn's stored 结论 as a clean `conclusion` field, so
    `render_history` can compress older turns to it instead of truncating."""
    out: list[dict[str, Any]] = []
    for m in repository.get_conversation_messages(conversation_id):
        if m["id"] == current_message_id:
            continue
        concl = _stored_conclusion(m)
        out.append({**m, "conclusion": concl} if concl else m)
    return out


def _stored_conclusion(message: dict[str, Any]) -> str:
    raw = message.get("metadata_json")
    if not raw:
        return ""
    try:
        meta = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return ""
    return str((meta or {}).get("conclusion", "")).strip()


def _build_topic_question() -> tuple[str, ChatState]:
    reply = "出生信息已经够了。你想先看哪个方向：事业、感情、财务，还是性格？"
    return reply, ChatState(
        topic=None,
        needs_more_info=False,
        missing_fields=[],
        suggested_followups=["事业怎么看？", "感情怎么看？", "财务怎么看？", "性格优势是什么？"],
    )


def _new_unique_analysis_id() -> str:
    # Collisions are unlikely; still try a few times before surfacing the DB error.
    for _ in range(5):
        candidate = new_analysis_id()
        if repository.get_analysis_package(candidate) is None:
            return candidate
    return new_analysis_id()
