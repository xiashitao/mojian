import { ThemeSwitcher } from "../../theme";
import { AccountMenu } from "../auth/AccountMenu";

export interface ChatHeaderProps {
  onToggleMobilePanel: () => void;
  onHome: () => void;
  /** 仅管理员且有会话时提供:打开本会话的跨轮调用追踪。 */
  onOpenTrace?: () => void;
}

/** Top bar of the chat column. The brand mark only shows on mobile (drawer). */
export function ChatHeader({ onToggleMobilePanel, onHome, onOpenTrace }: ChatHeaderProps) {
  return (
    <header className="chat-header">
      <button
        type="button"
        className="chat-header__nav"
        onClick={onToggleMobilePanel}
        aria-label="打开对话记录"
      >
        {/* 侧栏图标:带分栏线的面板。此前是单字「案」,脱离「案卷」上下文后不可读。 */}
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="3" width="12" height="10" rx="1.5" />
          <path d="M6 3v10" />
        </svg>
      </button>
      {/* 标题即返回首页入口:移动端没有别的常驻首页入口,点品牌回首页是通用预期。 */}
      <button
        type="button"
        className="chat-header__title"
        onClick={onHome}
        aria-label="返回首页"
      >
        <span className="chat-header__mark">Kairos</span>
        <span className="chat-header__sub">看清局势 · 把握时机</span>
      </button>
      <div className="chat-header__actions">
        {onOpenTrace && (
          <button
            type="button"
            className="chat-header__trace"
            onClick={onOpenTrace}
            aria-label="会话调用追踪"
            title="会话调用追踪（管理员）"
          >
            <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="4" cy="4" r="1.5" />
              <circle cx="4" cy="12" r="1.5" />
              <circle cx="12" cy="8" r="1.5" />
              <path d="M4 5.5v5M5.4 4.7 10.6 7.3M5.4 11.3 10.6 8.7" />
            </svg>
          </button>
        )}
        <AccountMenu />
        <ThemeSwitcher />
      </div>
    </header>
  );
}
