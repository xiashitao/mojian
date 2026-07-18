import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import {
  getAdminFeedback,
  getAdminRuns,
  type FeedbackItem,
  type RecentRun,
} from "../api/adminApi";
import "../styles/ops.css";

/** 运营后台首页:用户反馈(差评优先)+ 最近轮次,点击行进入会话详情。 */
export default function OpsPage() {
  const { user, loading } = useAuth();
  const [feedback, setFeedback] = useState<FeedbackItem[] | null>(null);
  const [runs, setRuns] = useState<RecentRun[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user || user.role !== "admin") return;
    getAdminFeedback()
      .then((d) => {
        const sorted = [...d.feedback].sort(
          (a, b) => Number(a.feedback !== "dislike") - Number(b.feedback !== "dislike"),
        );
        setFeedback(sorted);
      })
      .catch((e) => setError(e?.message ?? "加载失败"));
    getAdminRuns()
      .then((d) => setRuns(d.runs))
      .catch(() => {});
  }, [user]);

  if (loading) return null;
  if (!user || user.role !== "admin") return <Navigate to="/" replace />;

  return (
    <div className="ops">
      <header className="ops__head">
        <h1 className="ops__title">运营后台</h1>
        <Link className="ops__back" to="/session">
          ← 返回会话
        </Link>
      </header>

      {error && <div className="ops__error">{error}</div>}

      <section className="ops__section">
        <h2 className="ops__section-title">
          用户反馈{feedback ? `（${feedback.length}）` : ""}
        </h2>
        {feedback && feedback.length === 0 && (
          <div className="ops__empty">还没有用户反馈</div>
        )}
        <ul className="ops-list">
          {(feedback ?? []).map((f) => (
            <li key={f.analysis_id}>
              <Link
                className="ops-row"
                to={`/admin/conversations/${f.conversation_id}?focus=${f.analysis_id}`}
              >
                <span
                  className={`ops-row__mark ${
                    f.feedback === "dislike" ? "is-dislike" : "is-like"
                  }`}
                >
                  {f.feedback === "dislike" ? "踩" : "赞"}
                </span>
                <span className="ops-row__main">
                  <span className="ops-row__q">{f.user_message || "（无问题记录）"}</span>
                  <span className="ops-row__a">{f.reply_excerpt}…</span>
                  {f.comment && (
                    <span className="ops-row__comment">💬 {f.comment}</span>
                  )}
                </span>
                <span className="ops-row__meta">
                  {f.topic && <span className="ops-chip">{f.topic}</span>}
                  <span className="ops-row__time">{f.feedback_at}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section className="ops__section">
        <h2 className="ops__section-title">最近轮次</h2>
        <ul className="ops-list">
          {(runs ?? []).map((r) => (
            <li key={r.run_id}>
              <Link
                className="ops-row ops-row--run"
                to={`/admin/conversations/${r.conversation_id}?focus=${r.analysis_id}`}
              >
                <span className={`ops-chip ops-chip--${r.status}`}>{r.status}</span>
                <span className="ops-row__main">
                  <span className="ops-row__q">
                    {r.intent ?? "-"} {r.topic ? `· ${r.topic}` : ""}
                  </span>
                </span>
                <span className="ops-row__meta">
                  {r.latency_ms != null && (
                    <span className="ops-chip">{(r.latency_ms / 1000).toFixed(1)}s</span>
                  )}
                  {r.total_tokens != null && r.total_tokens > 0 && (
                    <span className="ops-chip">{r.total_tokens} tok</span>
                  )}
                  {r.cost != null && (
                    <span className="ops-chip">¥{r.cost.toFixed(4)}</span>
                  )}
                  <span className="ops-row__time">{r.started_at}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
