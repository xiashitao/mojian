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
        aria-label="案卷"
      >
        案
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
