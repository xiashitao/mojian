import { useEffect, useState } from "react";

export interface ComposerHint {
  id: string;
  text: string;
}

/**
 * Hints shown above the composer (PC only). Add more here — they rotate
 * vertically, always sliding upward, one every {@link ROTATE_MS}ms.
 */
export const COMPOSER_HINTS: ComposerHint[] = [
  { id: "send", text: "Enter 发送 · Shift+Enter 换行" },
  { id: "image", text: "Ctrl+V 添加图片" },
];

const ROTATE_MS = 3000;
const SLIDE_MS = 420;

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

export interface ComposerHintsProps {
  hints?: ComposerHint[];
}

/** Rotating composer hints — each shown for 3s, always sliding upward. */
export function ComposerHints({ hints = COMPOSER_HINTS }: ComposerHintsProps) {
  const [index, setIndex] = useState(0);
  const [animate, setAnimate] = useState(true);
  const count = hints.length;
  const reduceMotion = prefersReducedMotion();

  // Advance one step every ROTATE_MS, incrementing past the end into the
  // appended clone so each move goes up — never wrapping back down.
  useEffect(() => {
    if (count <= 1) return;
    const timer = window.setInterval(() => {
      setAnimate(true);
      setIndex((current) => current + 1);
    }, ROTATE_MS);
    return () => window.clearInterval(timer);
  }, [count]);

  // After sliding onto the cloned first hint, snap back to the real first hint
  // with no transition — invisible, since they're identical. Timer-based so it
  // works even when the slide is disabled (reduced motion).
  useEffect(() => {
    if (count <= 1 || index !== count) return;
    const reset = window.setTimeout(() => {
      setAnimate(false);
      setIndex(0);
    }, SLIDE_MS);
    return () => window.clearTimeout(reset);
  }, [index, count]);

  if (count === 0) return null;

  // Append a clone of the first hint to bridge the loop seamlessly.
  const items = count > 1 ? [...hints, hints[0]] : hints;
  const sliding = animate && !reduceMotion;

  return (
    <div className="composer__hints" aria-hidden="true">
      <div
        className="composer__hints-track"
        style={{
          transform: `translateY(-${index * 100}%)`,
          transition: sliding ? `transform ${SLIDE_MS}ms cubic-bezier(0.4, 0, 0.2, 1)` : "none",
        }}
      >
        {items.map((hint, i) => (
          <span key={`${hint.id}-${i}`} className="composer__hint">
            {hint.text}
          </span>
        ))}
      </div>
    </div>
  );
}
