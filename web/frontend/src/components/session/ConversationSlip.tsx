import type { ConversationSummary } from "../../types/api";
import { relativeTime } from "../../utils/sessionFormat";

export interface ConversationSlipProps {
  conversation: ConversationSummary;
  isActive: boolean;
  disabled: boolean;
  onSelect: (id: string) => void;
}

/** A single conversation entry in the archive list. */
export function ConversationSlip({
  conversation,
  isActive,
  disabled,
  onSelect,
}: ConversationSlipProps) {
  return (
    <button
      type="button"
      className={`slip ${isActive ? "is-active" : ""}`}
      onClick={() => onSelect(conversation.id)}
      disabled={disabled}
    >
      <div className="slip__edge" aria-hidden />
      <div className="slip__excerpt">{conversation.excerpt || "（无内容）"}</div>
      <div className="slip__foot">
        <span className="slip__time">
          {relativeTime(conversation.last_message_at)}
        </span>
        <span className="slip__count">{conversation.message_count}条</span>
      </div>
    </button>
  );
}
