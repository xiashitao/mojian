import type { KeyboardEvent } from "react";

export interface ComposerProps {
  value: string;
  loading: boolean;
  onChange: (value: string) => void;
  onSend: () => void;
  onStop: () => void;
}

/** Bottom composer: textarea, typing indicator and round send / stop button. */
export function Composer({ value, loading, onChange, onSend, onStop }: ComposerProps) {
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
            分析中
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
            {loading ? (
              <button
                type="button"
                className="composer__send composer__send--stop"
                onClick={onStop}
                aria-label="停止"
                title="停止（Esc）"
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                  <rect x="3.5" y="3.5" width="9" height="9" rx="1.5" />
                </svg>
              </button>
            ) : (
              <button
                type="button"
                className="composer__send"
                onClick={onSend}
                disabled={!value.trim()}
                aria-label="发送"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M2 8L14 2L8 14L7 9L2 8Z" />
                  <path d="M7 9L14 2" />
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
