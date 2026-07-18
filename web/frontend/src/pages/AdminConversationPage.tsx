import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth";
import {
  getAdminConversation,
  type AdminConversation,
  type AdminMessage,
} from "../api/adminApi";
import type { ConversationRun } from "../api/chatApi";
import { TraceModal } from "../components/session/TraceModal";
import "../styles/ops.css";

/** 一条消息 metadata 里运营关心的字段。 */
function parseMeta(json: string | null): { feedback?: string; feedback_comment?: string } {
  if (!json) return {};
  try {
    return JSON.parse(json) as { feedback?: string; feedback_comment?: string };
  } catch {
    return {};
  }
}

/** 运营视角的会话回放:对话式渲染,每条回复带元信息条(成本/耗时/token/反馈),
 * 点「查看链路」弹出该轮完整调用链(路由/工具/模型调用/记忆)。 */
export default function AdminConversationPage() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const [search] = useSearchParams();
  const focusAnalysisId = search.get("focus");
  const { user, loading } = useAuth();

  const [data, setData] = useState<AdminConversation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [traceFor, setTraceFor] = useState<string | null>(null);
  const focusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!conversationId || !user || user.role !== "admin") return;
    getAdminConversation(conversationId)
      .then(setData)
      .catch((e) => setError(e?.message ?? "加载失败"));
  }, [conversationId, user]);

  useEffect(() => {
    // 从反馈列表跳入时,定位到被反馈的那条回复。
    if (data && focusRef.current) {
      focusRef.current.scrollIntoView({ block: "center" });
    }
  }, [data]);

  if (loading) return null;
  if (!user || user.role !== "admin") return <Navigate to="/" replace />;

  const runByAnalysis = new Map<string, ConversationRun>(
    (data?.runs ?? []).map((r) => [r.analysis_id, r]),
  );

  return (
    <div className="ops ops--conv">
      <header className="ops__head">
        <h1 className="ops__title">会话回放</h1>
        <code className="ops__convid">{conversationId}</code>
        <Link className="ops__back" to="/admin/ops">
          ← 返回运营后台
        </Link>
      </header>

      {error && <div className="ops__error">{error}</div>}
      {!data && !error && <div className="ops__empty">加载中…</div>}

      <div className="ops-stream">
        {(data?.messages ?? []).map((m) => (
          <OpsMessage
            key={m.id}
            message={m}
            run={m.analysis_id ? runByAnalysis.get(m.analysis_id) : undefined}
            focused={!!m.analysis_id && m.analysis_id === focusAnalysisId}
            focusRef={m.analysis_id === focusAnalysisId ? focusRef : undefined}
            onOpenTrace={() => m.analysis_id && setTraceFor(m.analysis_id)}
          />
        ))}
      </div>

      {traceFor && (
        <TraceModal analysisId={traceFor} onClose={() => setTraceFor(null)} />
      )}
    </div>
  );
}

function OpsMessage({
  message,
  run,
  focused,
  focusRef,
  onOpenTrace,
}: {
  message: AdminMessage;
  run?: ConversationRun;
  focused: boolean;
  focusRef?: React.RefObject<HTMLElement | null>;
  onOpenTrace: () => void;
}) {
  const meta = parseMeta(message.metadata_json);
  const isAssistant = message.role === "assistant";

  return (
    <article
      ref={focusRef as React.RefObject<HTMLElement>}
      className={`ops-msg ops-msg--${message.role} ${focused ? "is-focused" : ""}`}
    >
      <div className="ops-msg__body">
        {isAssistant ? <Markdown>{message.content}</Markdown> : message.content}
      </div>

      {isAssistant && (
        <div className="ops-msg__meta">
          {meta.feedback && (
            <span
              className={`ops-row__mark ${
                meta.feedback === "dislike" ? "is-dislike" : "is-like"
              }`}
            >
              {meta.feedback === "dislike" ? "踩" : "赞"}
            </span>
          )}
          {meta.feedback_comment && (
            <span className="ops-msg__comment">💬 {meta.feedback_comment}</span>
          )}
          {run?.intent && <span className="ops-chip">{run.intent}</span>}
          {run?.topic && <span className="ops-chip">{run.topic}</span>}
          {run?.latency_ms != null && (
            <span className="ops-chip">{(run.latency_ms / 1000).toFixed(1)}s</span>
          )}
          {run != null && run.llm_calls > 0 && (
            <span className="ops-chip">
              {run.llm_calls} 次模型 · {run.total_tokens} tok
            </span>
          )}
          {run?.cost != null && (
            <span className="ops-chip ops-chip--cost">¥{run.cost.toFixed(4)}</span>
          )}
          {run?.error && <span className="ops-chip ops-chip--failed">出错</span>}
          {message.analysis_id && (
            <button type="button" className="ops-msg__trace" onClick={onOpenTrace}>
              查看链路
            </button>
          )}
        </div>
      )}
      <div className="ops-msg__time">{message.created_at}</div>
    </article>
  );
}
