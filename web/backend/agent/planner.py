"""MVP state machine for the chat agent."""
from __future__ import annotations

import json
import time
from collections.abc import Iterator
from typing import Any

from ..services import llm
from . import memory, repository
from .extractor import merge_birth_info
from .ids import new_analysis_id
from .models import ChatState, ConversationState, Topic
from .router import route
from .responder import (
    build_missing_info_reply,
    build_out_of_scope_reply,
    build_smalltalk_reply,
    stream_consultation_reply,
)
from .tools import run_bazibase_tools
from .tracing import TraceWriter


def stream_chat(message: str, conversation_id: str | None = None, *, user_id: str | None = None, memory_key: str | None = None) -> Iterator[str]:
    """Stream one user message response as newline-delimited JSON chunks.

    Yields:
        JSON lines of the form:
          {"type": "token", "text": "..."}   — incremental reply text
          {"type": "done", "conversation_id": ..., "analysis_id": ...,
           "state": {...}}                    — final metadata (last line)
          {"type": "error", "detail": "..."}  — on failure
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

    try:
        state = _load_state(conv_id)
        # Seed remembered birth info so returning users skip re-entering it.
        if not state.birth_info.is_complete():
            remembered = memory.get_birth_info(memory_key)
            if remembered:
                state.birth_info = merge_birth_info(remembered, state.birth_info)

        decision = route(message, state)
        intent = decision.intent
        topic = decision.topic
        merged_birth_info = decision.birth_info
        tracer.add("extract_input", input_data={"message": message},
                   output_data=decision.model_dump(),
                   summary=f"Routed to action={decision.action}.")

        state.birth_info = merged_birth_info
        state.current_topic = topic or state.current_topic
        state.last_analysis_id = analysis_id
        memory.save_birth_info(memory_key, merged_birth_info)
        tracer.add("merge_session_state",
                   input_data={"previous_state": repository.get_conversation_state(conv_id)},
                   output_data=state.model_dump(), summary="Merged session state.")

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
        else:
            tool_result = run_bazibase_tools(merged_birth_info)
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

            clarify = decision.action == "clarify"
            prior_messages = _prior_messages(conv_id, user_message["id"])
            past_notes = memory.recent_notes(memory_key)
            generation_trace = None
            for chunk, final_state, generation_trace in stream_consultation_reply(
                topic, tool_result,
                source_basis=state.source_basis,
                clarify_previous=clarify,
                user_message=message,
                history=prior_messages,
                memory_notes=past_notes,
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
                                conclusion=conclusion, analysis_id=analysis_id)
                tracer.add("update_memory", input_data={"topic": topic},
                           output_data={"conclusion": conclusion},
                           summary="Saved consultation conclusion to user memory.")

        full_reply = "".join(reply_parts)
        repository.update_conversation_state(conv_id, state.model_dump())
        assistant_message = repository.add_message(
            conv_id, "assistant", full_reply,
            analysis_id=analysis_id, metadata=chat_state.model_dump(),
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
    """Persisted turns before the current user message (for follow-up context)."""
    return [
        m
        for m in repository.get_conversation_messages(conversation_id)
        if m["id"] != current_message_id
    ]


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
