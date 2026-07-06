import Markdown from "react-markdown";
import type { MessageFeedback, UiMessage } from "../../types/session";
import { formatClock } from "../../utils/sessionFormat";
import { KairosLogo } from "../KairosLogo";
import { ChartCard } from "./ChartCard";

/**
 * CommonMark 的加粗定界符(flanking)规则在中文全角标点旁会失效:
 * `**结论：**今年` / `**（用神）**` 会原样吐出星号而不是加粗。
 * 渲染前把包在 ** 里的首尾全角标点挪到边界外(`**结论：**` → `**结论**：`),
 * 语义不变,加粗恢复解析。
 */
const BOLD_CJK_PUNCT_RE =
  /\*\*([（【「『"'《]*)([^*\n]+?)([：:，。、；！？…）】」』"'》]*)\*\*/g;

function normalizeMarkdown(text: string): string {
  return text.replace(BOLD_CJK_PUNCT_RE, "$1**$2**$3");
}

export interface MessageItemProps {
  message: UiMessage;
  loading: boolean;
  onSendFollowup: (text: string) => void;
  onFeedback: (id: string, feedback: MessageFeedback) => void;
}

/** A single message bubble with its meta, actions and follow-up chips. */
export function MessageItem({
  message,
  loading,
  onSendFollowup,
  onFeedback,
}: MessageItemProps) {
  const { id, role, content, pending, error, analysis_id, followups, feedback } =
    message;
  const clock = formatClock(message.created_at);
  const showActions = !pending && role === "assistant" && !error;
  const showFollowups =
    !pending && !error && followups && followups.length > 0;

  return (
    <article
      className={`message message--${role} ${pending ? "is-pending" : ""} ${
        error ? "is-error" : ""
      }`}
    >
      {message.chart && <ChartCard chart={message.chart} />}

      <div className="message__body">
        {pending && !content ? (
          <KairosLogo size={24} className="message__thinking" />
        ) : role === "assistant" ? (
          // 模型输出会带轻量 markdown(**加粗**等),按 markdown 渲染;
          // 用户消息保持纯文本,不解析用户输入里的标记。
          <Markdown>{normalizeMarkdown(content)}</Markdown>
        ) : (
          content
        )}
      </div>

      {!pending && role === "user" && clock && (
        <div className="message__time">{clock}</div>
      )}

      {!pending && analysis_id && (
        <div className="message__meta">
          <span className="message__id">{analysis_id}</span>
        </div>
      )}

      {showActions && (
        <div className="message__actions">
          <button
            type="button"
            className="msg-action"
            aria-label="复制"
            onClick={() => navigator.clipboard.writeText(content)}
          >
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
              <rect x="5" y="5" width="9" height="9" rx="1.5" />
              <path d="M11 5V3.5A1.5 1.5 0 0 0 9.5 2H3.5A1.5 1.5 0 0 0 2 3.5v6A1.5 1.5 0 0 0 3.5 11H5" />
            </svg>
          </button>
          <button
            type="button"
            className={`msg-action ${feedback === "like" ? "is-active" : ""}`}
            aria-label="有用"
            onClick={() => onFeedback(id, "like")}
          >
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 7 L7.5 2 Q8 1 9 1.5 L9 5 H13.5 Q14.5 5 14 6.5 L12.5 11.5 Q12 13 11 13 H7 Q6 13 6 12 V8 Q6 7 5 7 Z" />
              <path d="M5 7 H3.5 Q2 7 2 8 V12 Q2 13 3.5 13 H5" />
            </svg>
          </button>
          <button
            type="button"
            className={`msg-action ${feedback === "dislike" ? "is-active" : ""}`}
            aria-label="没用"
            onClick={() => onFeedback(id, "dislike")}
          >
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
              <path d="M11 9 L8.5 14 Q8 15 7 14.5 L7 11 H2.5 Q1.5 11 2 9.5 L3.5 4.5 Q4 3 5 3 H9 Q10 3 10 4 V8 Q10 9 11 9 Z" />
              <path d="M11 9 H12.5 Q14 9 14 8 V4 Q14 3 12.5 3 H11" />
            </svg>
          </button>
        </div>
      )}

      {showFollowups && (
        <div className="message__followups">
          {followups.map((f) => (
            <button
              key={f}
              type="button"
              className="followup-chip"
              onClick={() => onSendFollowup(f)}
              disabled={loading}
            >
              {f}
            </button>
          ))}
        </div>
      )}
    </article>
  );
}
