import { ThemeSwitcher } from "../../theme";
import { AccountMenu } from "../auth/AccountMenu";

export interface ChatHeaderProps {
  onToggleMobilePanel: () => void;
}

/** Top bar of the chat column. The brand mark only shows on mobile (drawer). */
export function ChatHeader({ onToggleMobilePanel }: ChatHeaderProps) {
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
      <div className="chat-header__title">
        <span className="chat-header__mark">Kairos</span>
        <span className="chat-header__sub">看清局势 · 把握时机</span>
      </div>
      <div className="chat-header__actions">
        <AccountMenu />
        <ThemeSwitcher />
      </div>
    </header>
  );
}
