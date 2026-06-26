import type { ConversationSummary } from "../../types/api";
import { KairosLogo } from "../KairosLogo";
import { ConversationSlip } from "./ConversationSlip";

export interface ArchiveSidebarProps {
  conversations: ConversationSummary[];
  conversationId: string | null;
  loadingConv: boolean;
  isOpen: boolean;
  onHome: () => void;
  onCollapse: () => void;
  onNew: () => void;
  onSelect: (id: string) => void;
}

/** Full left sidebar: brand, new-conversation action and the conversation list. */
export function ArchiveSidebar({
  conversations,
  conversationId,
  loadingConv,
  isOpen,
  onHome,
  onCollapse,
  onNew,
  onSelect,
}: ArchiveSidebarProps) {
  return (
    <aside className={`archive ${isOpen ? "is-open" : ""}`}>
      <div className="archive__brand">
        <button
          type="button"
          className="archive__brand-home"
          onClick={onHome}
          aria-label="返回首页"
        >
          <KairosLogo size={32} className="archive__brand-logo" />
          <span className="archive__brand-name">Kairos</span>
        </button>
        <button
          type="button"
          className="panel-collapse panel-collapse--archive"
          onClick={onCollapse}
          aria-label="收起案卷"
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10 4 6 8l4 4" />
          </svg>
        </button>
      </div>

      <div className="archive__head">
        <button
          type="button"
          className={`archive__new-sm ${!conversationId ? "is-active" : ""}`}
          onClick={onNew}
        >
          ＋ 新对话
        </button>
      </div>

      <div className="archive__list">
        {conversations.length === 0 && (
          <div className="archive__empty">
            <span>暂无对话</span>
            <span className="archive__empty-hint">发送第一条消息开始</span>
          </div>
        )}
        {conversations.map((conv) => (
          <ConversationSlip
            key={conv.id}
            conversation={conv}
            isActive={conv.id === conversationId}
            disabled={loadingConv}
            onSelect={onSelect}
          />
        ))}
      </div>
    </aside>
  );
}
