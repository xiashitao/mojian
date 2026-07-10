import { useEffect, useRef, useState } from "react";
import { getConversationRuns, type ConversationRun } from "../../api/chatApi";
import { TraceModal } from "./TraceModal";

interface Props {
  conversationId: string;
  onClose: () => void;
}

/** 跨轮追踪:一段会话的所有 run 排成时间线,每轮显示意图/话题/耗时/模型开销;
 *  点某一轮打开它的完整调用链(复用 TraceModal)。 */
export function ConversationTraceModal({ conversationId, onClose }: Props) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const [runs, setRuns] = useState<ConversationRun[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    getConversationRuns(conversationId)
      .then((d) => alive && setRuns(d.runs))
      .catch((e) => alive && setError(e?.message ?? "加载失败"));
    return () => {
      alive = false;
    };
  }, [conversationId]);

  useEffect(() => {
    dialogRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const totalTokens = (runs ?? []).reduce((n, r) => n + r.total_tokens, 0);
  const totalCalls = (runs ?? []).reduce((n, r) => n + r.llm_calls, 0);

  return (
    <div className="detail-scrim" onClick={onClose}>
      <div
        className="detail-modal trace-modal"
        role="dialog"
        aria-modal="true"
        aria-label="会话追踪"
        tabIndex={-1}
        ref={dialogRef}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="detail-modal__head">
          <span className="detail-modal__title">会话追踪</span>
          <button
            type="button"
            className="detail-modal__close"
            onClick={onClose}
            aria-label="关闭"
          >
            ✕
          </button>
        </div>

        <div className="detail-modal__body">
          {error && <div className="trace-error">{error}</div>}
          {!runs && !error && <div className="trace-placeholder">加载中…</div>}

          {runs && (
            <>
              <div className="trace-head">
                <div className="trace-head__stats">
                  <span className="trace-chip">{runs.length} 轮</span>
                  <span className="trace-chip">
                    {totalCalls} 次模型 · {totalTokens} tok
                  </span>
                </div>
              </div>

              {runs.length === 0 && (
                <div className="trace-placeholder">这段会话还没有追踪记录。</div>
              )}

              <ol className="trace-timeline">
                {runs.map((run, i) => {
                  const failed = run.status === "failed" || Boolean(run.error);
                  return (
                    <li
                      key={run.analysis_id}
                      className={`trace-turn ${failed ? "trace-step--fail" : ""}`}
                    >
                      <button
                        type="button"
                        className="trace-turn__btn"
                        onClick={() => setOpenId(run.analysis_id)}
                        title="查看这一轮的完整调用链"
                      >
                        <div className="trace-turn__head">
                          <span className="trace-step__idx">#{i + 1}</span>
                          <span className="trace-turn__msg">
                            {run.user_message || "（无输入）"}
                          </span>
                        </div>
                        <div className="trace-turn__meta">
                          <span className={`trace-chip trace-chip--${run.status}`}>
                            {run.status}
                          </span>
                          {run.intent && <span className="trace-chip">{run.intent}</span>}
                          {run.topic && <span className="trace-chip">{run.topic}</span>}
                          {run.latency_ms != null && (
                            <span className="trace-chip">{run.latency_ms}ms</span>
                          )}
                          <span className="trace-chip">
                            {run.llm_calls} 模型 · {run.total_tokens} tok
                          </span>
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ol>
            </>
          )}
        </div>
      </div>

      {openId && (
        <TraceModal analysisId={openId} onClose={() => setOpenId(null)} />
      )}
    </div>
  );
}
