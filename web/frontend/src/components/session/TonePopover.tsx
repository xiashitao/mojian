import { useEffect } from "react";

export type ToneId = "advisor" | "friend" | "direct";

export interface ToneOption {
  id: ToneId;
  label: string;
  desc: string;
}

/** Answer-tone presets. Default stays restrained per the product brand. */
export const TONE_OPTIONS: ToneOption[] = [
  { id: "advisor", label: "沉稳顾问", desc: "审慎克制，给有边界的参考" },
  { id: "friend", label: "温和朋友", desc: "亲切耐心，像朋友一样陪你聊" },
  { id: "direct", label: "直接利落", desc: "干脆直接，少铺垫" },
];

export const DEFAULT_TONE: ToneId = "advisor";

export function toneLabel(id: ToneId): string {
  return TONE_OPTIONS.find((opt) => opt.id === id)?.label ?? TONE_OPTIONS[0].label;
}

export interface TonePopoverProps {
  selected: ToneId;
  onSelect: (id: ToneId) => void;
  onClose: () => void;
}

/** Popover above the composer for picking the answer tone. */
export function TonePopover({ selected, onSelect, onClose }: TonePopoverProps) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      <div className="tone-popover__backdrop" onClick={onClose} />
      <div className="tone-popover" role="dialog" aria-label="回答语气">
        <div className="tone-popover__title">回答语气</div>
        <ul className="tone-popover__list">
          {TONE_OPTIONS.map((opt) => (
            <li key={opt.id}>
              <button
                type="button"
                className={
                  "tone-popover__option" + (opt.id === selected ? " is-selected" : "")
                }
                onClick={() => {
                  onSelect(opt.id);
                  onClose();
                }}
              >
                <span className="tone-popover__label">{opt.label}</span>
                <span className="tone-popover__desc">{opt.desc}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}
