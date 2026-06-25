import { useState, type KeyboardEvent } from "react";
import { ComposerHints } from "./ComposerHints";
import { TonePopover, toneLabel, type ToneId } from "./TonePopover";

export interface ComposerProps {
  value: string;
  loading: boolean;
  tone: ToneId;
  onToneChange: (tone: ToneId) => void;
  onChange: (value: string) => void;
  onSend: () => void;
  onStop: () => void;
}

/** Bottom composer: textarea, typing indicator, tone selector and send / stop button. */
export function Composer({ value, loading, tone, onToneChange, onChange, onSend, onStop }: ComposerProps) {
  const [toneOpen, setToneOpen] = useState(false);

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  };

  const toggleTone = () => setToneOpen((open) => !open);

  return (
    <div className="composer">
      <div className="composer__wrap">
        {/* Above the box: typing indicator while analysing, rotating hints (PC) when idle. */}
        {loading ? (
          <div className="composer__typing">
            <span className="composer__typing-dots">
              <span />
              <span />
              <span />
            </span>
            分析中
          </div>
        ) : (
          <ComposerHints />
        )}

        <div className="composer__box">
          {/* Mobile-only: a plus that rotates 45° and opens the tone popover. */}
          <button
            type="button"
            className={"composer__plus" + (toneOpen ? " is-open" : "")}
            onClick={toggleTone}
            aria-label="更多选项"
            aria-expanded={toneOpen}
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round">
              <path d="M9 3.5v11M3.5 9h11" />
            </svg>
          </button>

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
            {/* PC-only: labelled tone button. */}
            <button
              type="button"
              className={"composer__tool" + (toneOpen ? " is-open" : "")}
              onClick={toggleTone}
              aria-expanded={toneOpen}
            >
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
                <path d="M2.5 4.5h11v6H6l-2.5 2v-2h-1z" />
              </svg>
              <span>{toneLabel(tone)}</span>
            </button>

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

        {toneOpen && (
          <TonePopover
            selected={tone}
            onSelect={onToneChange}
            onClose={() => setToneOpen(false)}
          />
        )}
      </div>
    </div>
  );
}
