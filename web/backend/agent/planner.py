"""MVP state machine for the chat agent."""
from __future__ import annotations

import json
import time
from collections.abc import Iterator
from typing import Any

from ..config import settings
from . import repository
from .extractor import extract_message, merge_birth_info
from .ids import new_analysis_id
from .models import BirthInfo, ChatState, ConversationState, Topic
from .responder import build_consultation_reply, build_missing_info_reply, stream_consultation_reply
from .tools import run_bazibase_tools
from .tracing import TraceWriter


def handle_chat(message: str, conversation_id: str | None = None) -> dict[str, Any]:
    """Handle one user message and return the API response payload."""
    started = time.monotonic()
    conversation = repository.ensure_conversation(conversation_id)
    conv_id = conversation["id"]
    user_message = repository.add_message(conv_id, "user", message)
    analysis_id = _new_unique_analysis_id()
    run = repository.create_agent_run(
        conv_id,
        user_message["id"],
        analysis_id,
        model=settings.deepseek_model if settings.deepseek_api_key else "deterministic",
    )
    tracer = TraceWriter(run["id"])

    assistant_message_id: str | None = None
    intent: str | None = None
    topic: Topic | None = None
    status = "success"
    error: str | None = None

    try:
        extraction = extract_message(message)
        intent = extraction.intent
        tracer.add(
            "extract_input",
            input_data={"message": message},
            output_data=extraction.dict(),
            summary="Extracted intent, topic, and birth information from user message.",
        )

        state = _load_state(conv_id)
        topic = _resolve_topic(extraction.topic, state.current_topic, extraction.intent)
        merged_birth_info = merge_birth_info(state.birth_info, extraction.birth_info)
        state.birth_info = merged_birth_info
        state.current_topic = topic or state.current_topic
        state.last_analysis_id = analysis_id
        tracer.add(
            "merge_session_state",
            input_data={"previous_state": repository.get_conversation_state(conv_id)},
            output_data=state.dict(),
            summary="Merged extracted fields into conversation state.",
        )

        if _should_ask_topic(extraction.intent, topic, merged_birth_info):
            reply, chat_state = _build_topic_question()
            generation_trace = {
                "mode": "topic_question",
                "reply": reply,
                "raw_response": None,
                "source_basis": state.source_basis,
            }
            tracer.add(
                "generate_reply",
                input_data={"intent": intent, "topic": topic},
                output_data=generation_trace,
                summary="Asked user to choose a consultation topic.",
            )
        elif not merged_birth_info.is_complete():
            reply, chat_state = build_missing_info_reply(topic, merged_birth_info)
            generation_trace = {
                "mode": "missing_info_followup",
                "reply": reply,
                "raw_response": None,
                "source_basis": state.source_basis,
            }
            tracer.add(
                "generate_reply",
                input_data={"missing_fields": merged_birth_info.complete_missing_fields()},
                output_data=generation_trace,
                summary="Asked for missing birth information.",
            )
        else:
            tool_result = run_bazibase_tools(merged_birth_info)
            tracer.add(
                "cast_chart",
                input_data=merged_birth_info.dict(),
                output_data=tool_result["chart"],
                summary="Casted Ba Zi chart.",
            )
            tracer.add(
                "diagnose",
                input_data={"chart_summary": tool_result["chart"].get("chart_summary")},
                output_data=tool_result["diagnosis"],
                summary=tool_result.get("diagnosis_summary"),
            )
            tracer.add(
                "prepare_arbitration",
                input_data={"diagnosis_summary": tool_result.get("diagnosis_summary")},
                output_data=tool_result["arbitration"],
                summary=(
                    f"Detected {tool_result['arbitration']['summary']['total']} arbitration cases. "
                    f"Resolved: {tool_result['arbitration']['summary']['resolved']}, "
                    f"Unresolved: {tool_result['arbitration']['summary']['unresolved']}."
                ),
            )

            clarify = extraction.intent == "clarify_previous"
            reply, chat_state, generation_trace = build_consultation_reply(
                topic,
                tool_result,
                source_basis=state.source_basis,
                clarify_previous=clarify,
            )
            tracer.add(
                "generate_reply",
                input_data={
                    "topic": topic,
                    "intent": intent,
                    "source_basis": state.source_basis,
                },
                output_data=generation_trace,
                summary="Generated user-facing consultation reply.",
            )

        repository.update_conversation_state(conv_id, state.dict())
        tracer.add(
            "persist_state",
            input_data={},
            output_data=state.dict(),
            summary="Persisted conversation state.",
        )
        assistant_message = repository.add_message(
            conv_id,
            "assistant",
            reply,
            analysis_id=analysis_id,
            metadata=chat_state.dict(),
        )
        assistant_message_id = assistant_message["id"]
    except Exception as exc:
        status = "failed"
        error = str(exc)
        reply = "这轮分析处理失败了。你可以把分析 ID 发给运营排查。"
        chat_state = ChatState(
            topic=topic,
            needs_more_info=False,
            missing_fields=[],
            suggested_followups=[],
        )
        tracer.add(
            "error",
            input_data={"message": message},
            output_data={"error": error},
            summary="Agent run failed.",
        )
        assistant_message = repository.add_message(
            conv_id,
            "assistant",
            reply,
            analysis_id=analysis_id,
            metadata=chat_state.dict(),
        )
        assistant_message_id = assistant_message["id"]

    repository.finish_agent_run(
        run["id"],
        assistant_message_id=assistant_message_id,
        status=status,
        intent=intent,
        topic=topic,
        started_monotonic=started,
        error=error,
        metadata={"analysis_id": analysis_id},
    )

    return {
        "conversation_id": conv_id,
        "analysis_id": analysis_id,
        "reply": reply,
        "state": chat_state.dict(),
    }


def stream_chat(message: str, conversation_id: str | None = None) -> Iterator[str]:
    """Stream one user message response as newline-delimited JSON chunks.

    Yields:
        JSON lines of the form:
          {"type": "token", "text": "..."}   — incremental reply text
          {"type": "done", "conversation_id": ..., "analysis_id": ...,
           "state": {...}}                    — final metadata (last line)
          {"type": "error", "detail": "..."}  — on failure
    """
    started = time.monotonic()
    conversation = repository.ensure_conversation(conversation_id)
    conv_id = conversation["id"]
    user_message = repository.add_message(conv_id, "user", message)
    analysis_id = _new_unique_analysis_id()
    run = repository.create_agent_run(
        conv_id,
        user_message["id"],
        analysis_id,
        model=settings.deepseek_model if settings.deepseek_api_key else "deterministic",
    )
    tracer = TraceWriter(run["id"])

    intent: str | None = None
    topic: Topic | None = None
    status = "success"
    error: str | None = None
    reply_parts: list[str] = []
    chat_state = ChatState(topic=None, needs_more_info=False, missing_fields=[], suggested_followups=[])

    try:
        extraction = extract_message(message)
        intent = extraction.intent
        tracer.add("extract_input", input_data={"message": message},
                   output_data=extraction.dict(),
                   summary="Extracted intent, topic, and birth information.")

        state = _load_state(conv_id)
        topic = _resolve_topic(extraction.topic, state.current_topic, extraction.intent)
        merged_birth_info = merge_birth_info(state.birth_info, extraction.birth_info)
        state.birth_info = merged_birth_info
        state.current_topic = topic or state.current_topic
        state.last_analysis_id = analysis_id
        tracer.add("merge_session_state",
                   input_data={"previous_state": repository.get_conversation_state(conv_id)},
                   output_data=state.dict(), summary="Merged session state.")

        if _should_ask_topic(extraction.intent, topic, merged_birth_info):
            reply, chat_state = _build_topic_question()
            yield json.dumps({"type": "token", "text": reply}, ensure_ascii=False) + "\n"
            reply_parts.append(reply)
        elif not merged_birth_info.is_complete():
            reply, chat_state = build_missing_info_reply(topic, merged_birth_info)
            yield json.dumps({"type": "token", "text": reply}, ensure_ascii=False) + "\n"
            reply_parts.append(reply)
        else:
            tool_result = run_bazibase_tools(merged_birth_info)
            tracer.add("cast_chart", input_data=merged_birth_info.dict(),
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

            clarify = extraction.intent == "clarify_previous"
            for chunk, final_state, generation_trace in stream_consultation_reply(
                topic, tool_result,
                source_basis=state.source_basis,
                clarify_previous=clarify,
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

        full_reply = "".join(reply_parts)
        repository.update_conversation_state(conv_id, state.dict())
        assistant_message = repository.add_message(
            conv_id, "assistant", full_reply,
            analysis_id=analysis_id, metadata=chat_state.dict(),
        )
        tracer.add("persist_state", input_data={}, output_data=state.dict(),
                   summary="Persisted conversation state.")

    except Exception as exc:
        status = "failed"
        error = str(exc)
        err_reply = "分析未能完成，请稍后再试。"
        reply_parts.append(err_reply)
        yield json.dumps({"type": "error", "detail": error}, ensure_ascii=False) + "\n"
        repository.add_message(conv_id, "assistant", err_reply, analysis_id=analysis_id,
                               metadata=chat_state.dict())
        tracer.add("error", input_data={"message": message},
                   output_data={"error": error}, summary="Agent run failed.")

    repository.finish_agent_run(
        run["id"],
        assistant_message_id=None,
        status=status, intent=intent, topic=topic,
        started_monotonic=started, error=error,
        metadata={"analysis_id": analysis_id},
    )

    yield json.dumps({
        "type": "done",
        "conversation_id": conv_id,
        "analysis_id": analysis_id,
        "state": chat_state.dict(),
    }, ensure_ascii=False) + "\n"


def _load_state(conversation_id: str) -> ConversationState:
    data = repository.get_conversation_state(conversation_id)
    if not data:
        return ConversationState()
    try:
        return ConversationState(**data)
    except Exception:
        return ConversationState()


def _resolve_topic(
    extracted: Topic | None,
    current: Topic | None,
    intent: str,
) -> Topic | None:
    if extracted:
        return extracted
    if intent == "clarify_previous":
        return current
    return current


def _should_ask_topic(intent: str, topic: Topic | None, birth_info: BirthInfo) -> bool:
    return birth_info.is_complete() and topic is None and intent in ("collect_birth_info", "unknown")


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

