"""SQLite repository for chat conversations and traces."""
from __future__ import annotations

import json
import time
from typing import Any

from ..database import get_db
from .ids import new_id


def _dump(data: Any) -> str:
    return json.dumps(data if data is not None else {}, ensure_ascii=False)


def _load(text: str | None, default: Any) -> Any:
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def ensure_conversation(conversation_id: str | None, *, user_id: str | None = None) -> dict:
    """Load an existing conversation or create a new one."""
    conn = get_db()
    try:
        if conversation_id:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
            if row:
                return _row_to_dict(row)

        new_conversation_id = new_id("conv")
        conn.execute(
            """INSERT INTO conversations (id, user_id, title, last_message_at, metadata_json)
               VALUES (?, ?, ?, datetime('now'), ?)""",
            (new_conversation_id, user_id, "新咨询", _dump({})),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (new_conversation_id,)
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def get_conversation(conversation_id: str) -> dict | None:
    """Return one conversation row by ID."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        return _row_to_dict(row, parse_json=True) if row else None
    finally:
        conn.close()


def add_message(
    conversation_id: str,
    role: str,
    content: str,
    *,
    analysis_id: str | None = None,
    metadata: dict | None = None,
) -> dict:
    message_id = new_id("msg")
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO messages
               (id, conversation_id, role, content, analysis_id, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (message_id, conversation_id, role, content, analysis_id, _dump(metadata)),
        )
        conn.execute(
            """UPDATE conversations
               SET updated_at = datetime('now'), last_message_at = datetime('now')
               WHERE id = ?""",
            (conversation_id,),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def create_agent_run(
    conversation_id: str,
    trigger_message_id: str,
    public_analysis_id: str,
    *,
    model: str | None = None,
) -> dict:
    run_id = new_id("run")
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO agent_runs
               (id, conversation_id, trigger_message_id, public_analysis_id, model)
               VALUES (?, ?, ?, ?, ?)""",
            (run_id, conversation_id, trigger_message_id, public_analysis_id, model),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def finish_agent_run(
    run_id: str,
    *,
    assistant_message_id: str | None,
    status: str,
    intent: str | None,
    topic: str | None,
    started_monotonic: float,
    error: str | None = None,
    metadata: dict | None = None,
) -> None:
    latency_ms = int((time.monotonic() - started_monotonic) * 1000)
    conn = get_db()
    try:
        conn.execute(
            """UPDATE agent_runs
               SET assistant_message_id = ?,
                   status = ?,
                   intent = ?,
                   topic = ?,
                   finished_at = datetime('now'),
                   latency_ms = ?,
                   error = ?,
                   metadata_json = ?
               WHERE id = ?""",
            (
                assistant_message_id,
                status,
                intent,
                topic,
                latency_ms,
                error,
                _dump(metadata),
                run_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def add_trace(
    run_id: str,
    step_index: int,
    step_type: str,
    *,
    input_data: Any = None,
    output_data: Any = None,
    summary: str | None = None,
) -> dict:
    trace_id = new_id("trace")
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO run_traces
               (id, run_id, step_index, step_type, input_json, output_json, summary)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                trace_id,
                run_id,
                step_index,
                step_type,
                _dump(input_data),
                _dump(output_data),
                summary,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM run_traces WHERE id = ?", (trace_id,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def list_conversations(limit: int = 50, user_id: str | None = None) -> list[dict]:
    """List a single owner's conversations, most recent first.

    Requires an owner key (logged-in user id or anonymous id). Without one we
    return nothing rather than leaking every conversation in the database.
    """
    if not user_id:
        return []
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT
                   c.id, c.title, c.metadata_json, c.status,
                   c.created_at, c.updated_at, c.last_message_at,
                   (SELECT COUNT(*) FROM messages m
                    WHERE m.conversation_id = c.id) AS message_count,
                   (SELECT m2.content FROM messages m2
                    WHERE m2.conversation_id = c.id AND m2.role = 'user'
                    ORDER BY m2.created_at ASC LIMIT 1) AS excerpt
               FROM conversations c
               WHERE c.status = 'active' AND c.user_id = ?
               ORDER BY c.last_message_at DESC, c.created_at DESC
               LIMIT ?""",
            (user_id, limit),
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            meta = _load(d.pop("metadata_json", None), {})
            birth = meta.get("birth_info") or {}
            result.append({
                "id": d["id"],
                "title": d.get("title") or "新命理咨询",
                "topic": (meta.get("current_topic") or {}).get("value")
                    if isinstance(meta.get("current_topic"), dict)
                    else meta.get("current_topic"),
                "gender": birth.get("gender"),
                "message_count": d.get("message_count", 0),
                "excerpt": (d.get("excerpt") or "")[:80],
                "created_at": d.get("created_at"),
                "updated_at": d.get("updated_at"),
                "last_message_at": d.get("last_message_at"),
            })
        return result
    finally:
        conn.close()


def get_conversation_messages(conversation_id: str) -> list[dict]:
    """Return all messages for a conversation in chronological order."""
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT * FROM messages
               WHERE conversation_id = ?
               ORDER BY created_at ASC, id ASC""",
            (conversation_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_conversation_state(conversation_id: str) -> dict:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT metadata_json FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        if not row:
            return {}
        return _load(row["metadata_json"], {})
    finally:
        conn.close()


def update_conversation_state(conversation_id: str, metadata: dict) -> None:
    conn = get_db()
    try:
        conn.execute(
            """UPDATE conversations
               SET metadata_json = ?, updated_at = datetime('now')
               WHERE id = ?""",
            (_dump(metadata), conversation_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_analysis_package(analysis_id: str) -> dict | None:
    conn = get_db()
    try:
        run = conn.execute(
            "SELECT * FROM agent_runs WHERE public_analysis_id = ?", (analysis_id,)
        ).fetchone()
        if not run:
            return None
        run_dict = _row_to_dict(run)
        conversation = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (run_dict["conversation_id"],)
        ).fetchone()
        messages = conn.execute(
            """SELECT * FROM messages
               WHERE conversation_id = ?
               ORDER BY created_at ASC, id ASC""",
            (run_dict["conversation_id"],),
        ).fetchall()
        traces = conn.execute(
            """SELECT * FROM run_traces
               WHERE run_id = ?
               ORDER BY step_index ASC, created_at ASC""",
            (run_dict["id"],),
        ).fetchall()

        trace_dicts = [_row_to_dict(t, parse_json=True) for t in traces]
        return {
            "analysis": {
                "analysis_id": analysis_id,
                "status": run_dict["status"],
                "intent": run_dict["intent"],
                "topic": run_dict["topic"],
                "latency_ms": run_dict["latency_ms"],
                "error": run_dict["error"],
            },
            "conversation": _row_to_dict(conversation, parse_json=True) if conversation else None,
            "messages": [_row_to_dict(m, parse_json=True) for m in messages],
            "agent_run": _row_to_dict(run, parse_json=True),
            "run_traces": trace_dicts,
            "chart": _latest_trace_output(trace_dicts, "cast_chart"),
            "diagnosis": _latest_trace_output(trace_dicts, "diagnose"),
            "arbitration": _latest_trace_output(trace_dicts, "prepare_arbitration"),
            "llm": {
                "reply_generation": _latest_trace_output(trace_dicts, "generate_reply"),
                "arbitration": _latest_trace_output(trace_dicts, "call_arbitration_llm"),
            },
        }
    finally:
        conn.close()


def get_conversation_runs(conversation_id: str) -> list[dict]:
    """一段会话里每一轮 run 的概要 + LLM 聚合(调用次数/总 token),按时间正序。

    支撑跨轮追踪时间线:一眼看清整段对话每轮的意图/话题/状态/耗时/模型开销,
    点某一轮再看它的完整调用链(get_analysis_package)。
    token 用 SQLite json_extract 从 llm_call 步骤的 output_json 里就地累加。
    """
    conn = get_db()
    try:
        runs = conn.execute(
            """SELECT r.id AS run_id, r.public_analysis_id AS analysis_id,
                      r.status, r.intent, r.topic, r.latency_ms, r.started_at, r.error,
                      m.content AS user_message
               FROM agent_runs r
               LEFT JOIN messages m ON m.id = r.trigger_message_id
               WHERE r.conversation_id = ?
               ORDER BY r.started_at ASC, r.rowid ASC""",
            (conversation_id,),
        ).fetchall()
        result = []
        for row in runs:
            d = _row_to_dict(row)
            stats = conn.execute(
                """SELECT COUNT(*) AS llm_calls,
                          COALESCE(SUM(CAST(
                              json_extract(output_json, '$.total_tokens') AS INTEGER
                          )), 0) AS total_tokens
                   FROM run_traces
                   WHERE run_id = ? AND step_type = 'llm_call'""",
                (d["run_id"],),
            ).fetchone()
            msg = d.get("user_message") or ""
            result.append({
                "analysis_id": d["analysis_id"],
                "status": d["status"],
                "intent": d["intent"],
                "topic": d["topic"],
                "latency_ms": d["latency_ms"],
                "started_at": d["started_at"],
                "error": d["error"],
                "user_message": msg if len(msg) <= 80 else msg[:80] + "…",
                "llm_calls": stats["llm_calls"],
                "total_tokens": stats["total_tokens"],
            })
        return result
    finally:
        conn.close()


def _latest_trace_output(traces: list[dict], step_type: str) -> Any:
    for trace in reversed(traces):
        if trace.get("step_type") == step_type:
            return trace.get("output_json")
    return None


def _row_to_dict(row, *, parse_json: bool = False) -> dict:
    data = dict(row)
    if parse_json:
        for key in ("metadata_json", "input_json", "output_json"):
            if key in data:
                data[key] = _load(data[key], {})
    return data
