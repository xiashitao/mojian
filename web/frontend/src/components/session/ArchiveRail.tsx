import { KairosLogo } from "../KairosLogo";

export interface ArchiveRailProps {
  onHome: () => void;
  onExpand: () => void;
  onNew: () => void;
}

/** Collapsed mini rail shown on desktop when the archive is hidden. */
export function ArchiveRail({ onHome, onExpand, onNew }: ArchiveRailProps) {
  return (
    <aside className="archive-rail" aria-label="案卷（已收起）">
      <KairosLogo
        size={30}
        className="archive-rail__logo"
        role="button"
        onClick={onHome}
      />
      <button
        type="button"
        className="archive-rail__btn"
        onClick={onExpand}
        aria-label="展开案卷"
        data-tooltip="展开"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 4l4 4-4 4" />
        </svg>
      </button>
      <button
        type="button"
        className="archive-rail__btn"
        onClick={onNew}
        aria-label="新对话"
        data-tooltip="新对话"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 3H4A1.5 1.5 0 0 0 2.5 4.5v7A1.5 1.5 0 0 0 4 13h7a1.5 1.5 0 0 0 1.5-1.5V8" />
          <path d="M11.4 2.4 13.6 4.6l-5.3 5.3H6.1V7.7z" />
        </svg>
      </button>
    </aside>
  );
}
