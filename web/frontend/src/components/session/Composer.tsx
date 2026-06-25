import type { KeyboardEvent } from "react";

export interface ComposerProps {
  value: string;
  loading: boolean;
  onChange: (value: string) => void;
  onSend: () => void;
}

/** Bottom composer: textarea, typing indicator and round send button. */
export function Composer({ value, loading, onChange, onSend }: ComposerProps) {
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  };

  return (
    <div className="composer">
      <div className="composer__wrap">
        {loading && (
          <div className="composer__typing">
            <span className="composer__typing-dots">
              <span />
              <span />
              <span />
            </span>
            正在推演…
          </div>
        )}
        <div className="composer__box">
          <textarea
            className="composer__input"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="出生日期、地点、性别，以及你想了解的问题。"
            autoComplete="off"
            rows={1}
          />
          <div className="composer__toolbar">
            <span className="composer__hint">Enter 发送 · Shift+Enter 换行</span>
            <button
              type="button"
              className="composer__send"
              onClick={onSend}
              disabled={loading || !value.trim()}
              aria-label="发送"
            >
              {loading ? (
                <svg className="composer__spinner" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                  <circle cx="8" cy="8" r="6" strokeOpacity="0.25" />
                  <path d="M8 2a6 6 0 0 1 6 6" />
                </svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M2 8L14 2L8 14L7 9L2 8Z" />
                  <path d="M7 9L14 2" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
