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


def add_run_cost(
    run_id: str,
    conversation_id: str,
    *,
    llm_calls: int,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    cost: float | None,
    models: dict | None = None,
) -> None:
    """记一轮 run 的 LLM 开销(CostMeter observer 在 run 结束时调用)。

    INSERT OR REPLACE:同 run 重复写入以最后一次为准(正常不会发生,防御性)。
    """
    conn = get_db()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO run_costs
               (run_id, conversation_id, llm_calls, prompt_tokens,
                completion_tokens, total_tokens, cost, models_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, conversation_id, llm_calls, prompt_tokens,
             completion_tokens, total_tokens, cost, _dump(models)),
        )
        conn.commit()
    finally:
        conn.close()


def set_message_feedback(
    analysis_id: str,
    *,
    owner_key: str | None,
    feedback: str | None,
    comment: str | None = None,
) -> dict | None:
    """给某轮回复记用户反馈,存进助手消息的 metadata_json。

    以 analysis_id 为键(前端流式期间只有它是稳定标识);归属校验:该轮所在
    会话的 user_id 必须等于 owner_key,否则视同不存在(404 语义,不泄露存在性)。
    feedback: "like" | "dislike" | None(None = 撤销,连评论一起清掉)。
    返回结果概要;找不到或不属于该用户时返回 None。
    """
    if not owner_key:
        return None
    conn = get_db()
    try:
        row = conn.execute(
            """SELECT r.assistant_message_id AS mid, c.user_id AS owner
               FROM agent_runs r JOIN conversations c ON c.id = r.conversation_id
               WHERE r.public_analysis_id = ?""",
            (analysis_id,),
        ).fetchone()
        if not row or not row["mid"] or row["owner"] != owner_key:
            return None
        meta_row = conn.execute(
            "SELECT metadata_json FROM messages WHERE id = ?", (row["mid"],)
        ).fetchone()
        meta = _load(meta_row["metadata_json"] if meta_row else None, {})
        if feedback is None:
            for key in ("feedback", "feedback_comment", "feedback_at"):
                meta.pop(key, None)
        else:
            meta["feedback"] = feedback
            if comment and comment.strip():
                meta["feedback_comment"] = comment.strip()[:500]
            else:
                meta.pop("feedback_comment", None)
            meta["feedback_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        conn.execute(
            "UPDATE messages SET metadata_json = ? WHERE id = ?",
            (_dump(meta), row["mid"]),
        )
        conn.commit()
        return {"analysis_id": analysis_id, "feedback": feedback}
    finally:
        conn.close()


def list_feedback(days: int = 30, limit: int = 100) -> list[dict]:
    """近期带反馈的轮次(新→旧)——运营排查入口:看到差评,拿 analysis_id
    直接开该轮 trace。"""
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT json_extract(m.metadata_json, '$.feedback')         AS feedback,
                      json_extract(m.metadata_json, '$.feedback_comment') AS comment,
                      json_extract(m.metadata_json, '$.feedback_at')      AS feedback_at,
                      m.analysis_id, m.conversation_id,
                      substr(m.content, 1, 80)                            AS reply_excerpt,
                      r.intent, r.topic,
                      (SELECT substr(um.content, 1, 80) FROM messages um
                       WHERE um.id = r.trigger_message_id)                AS user_message
               FROM messages m
               JOIN agent_runs r ON r.public_analysis_id = m.analysis_id
               WHERE json_extract(m.metadata_json, '$.feedback') IS NOT NULL
                 AND m.created_at >= datetime('now', ?)
               ORDER BY json_extract(m.metadata_json, '$.feedback_at') DESC
               LIMIT ?""",
            (f"-{days} days", limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_run_with_traces(ref: str) -> dict | None:
    """按 run_id 或 public_analysis_id 取一轮 run 及其全部 trace(调用链视图用)。"""
    conn = get_db()
    try:
        run = conn.execute(
            "SELECT * FROM agent_runs WHERE id = ? OR public_analysis_id = ?",
            (ref, ref),
        ).fetchone()
        if not run:
            return None
        run_dict = _row_to_dict(run)
        traces = conn.execute(
            """SELECT * FROM run_traces
               WHERE run_id = ?
               ORDER BY step_index ASC, created_at ASC""",
            (run_dict["id"],),
        ).fetchall()
        return {
            "run": run_dict,
            "traces": [_row_to_dict(t, parse_json=True) for t in traces],
        }
    finally:
        conn.close()


def recent_runs(limit: int = 20) -> list[dict]:
    """最近 N 轮 run 的概要(排查入口):状态/耗时/错误/开销。"""
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT r.id AS run_id, r.public_analysis_id AS analysis_id,
                      r.status, r.intent, r.topic, r.latency_ms,
                      r.started_at, r.error,
                      c.llm_calls, c.total_tokens, c.cost
               FROM agent_runs r
               LEFT JOIN run_costs c ON c.run_id = r.id
               ORDER BY r.started_at DESC, r.rowid DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def cost_summary(days: int = 7) -> dict:
    """成本报表:近 N 天按天聚合 + 按模型聚合(模型明细从 models_json 展开)。

    cost 里的 NULL(无定价模型)聚合时被 SUM 自然跳过;covered 标出有价可算的
    run 占比,报表读的人能看出「这个总额覆盖了多少调用」。
    """
    conn = get_db()
    try:
        by_day = [dict(r) for r in conn.execute(
            """SELECT date(created_at) AS day,
                      COUNT(*) AS runs,
                      SUM(llm_calls) AS llm_calls,
                      SUM(total_tokens) AS total_tokens,
                      ROUND(SUM(cost), 4) AS cost,
                      SUM(cost IS NOT NULL) AS priced_runs
               FROM run_costs
               WHERE created_at >= datetime('now', ?)
               GROUP BY day ORDER BY day DESC""",
            (f"-{days} days",),
        ).fetchall()]
        by_model = [dict(r) for r in conn.execute(
            """SELECT m.key AS model,
                      SUM(json_extract(m.value, '$.calls')) AS calls,
                      SUM(json_extract(m.value, '$.prompt_tokens')) AS prompt_tokens,
                      SUM(json_extract(m.value, '$.completion_tokens')) AS completion_tokens,
                      ROUND(SUM(json_extract(m.value, '$.cost')), 4) AS cost
               FROM run_costs, json_each(run_costs.models_json) AS m
               WHERE created_at >= datetime('now', ?)
               GROUP BY model ORDER BY cost DESC""",
            (f"-{days} days",),
        ).fetchall()]
        return {"days": days, "by_day": by_day, "by_model": by_model}
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
