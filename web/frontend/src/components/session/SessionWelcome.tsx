import type { ReactNode } from "react";
import { KairosLogo } from "../KairosLogo";

export interface SessionWelcomeProps {
  onPick: (text: string) => void;
}

type Starter = {
  text: string;
  icon: ReactNode;
};

const ICON_PROPS = {
  width: 16,
  height: 16,
  viewBox: "0 0 16 16",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.4,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

const STARTERS: Starter[] = [
  {
    text: "我适合创业还是稳定上班？",
    icon: (
      <svg {...ICON_PROPS}>
        <rect x="2.5" y="5" width="11" height="8" rx="1.5" />
        <path d="M6 5V3.5h4V5" />
      </svg>
    ),
  },
  {
    text: "最近适合换工作吗？",
    icon: (
      <svg {...ICON_PROPS}>
        <path d="M3 7a5 5 0 0 1 8.5-2.5L13 6" />
        <path d="M13 3.5V6h-2.5" />
        <path d="M13 9a5 5 0 0 1-8.5 2.5L3 10" />
        <path d="M3 12.5V10h2.5" />
      </svg>
    ),
  },
  {
    text: "我的性格优势和短板是什么？",
    icon: (
      <svg {...ICON_PROPS}>
        <circle cx="8" cy="5.5" r="2.5" />
        <path d="M3.5 13a4.5 4.5 0 0 1 9 0" />
      </svg>
    ),
  },
  {
    text: "感情上我适合怎样的人？",
    icon: (
      <svg {...ICON_PROPS}>
        <path d="M8 13S2.5 9.5 2.5 6.2A2.7 2.7 0 0 1 8 4.8a2.7 2.7 0 0 1 5.5 1.4C13.5 9.5 8 13 8 13Z" />
      </svg>
    ),
  },
  {
    text: "今年财运怎么走？",
    icon: (
      <svg {...ICON_PROPS}>
        <circle cx="8" cy="8" r="5.5" />
        <path d="M6 6l2 2.5L10 6M8 8.5V11M6.3 9h3.4" />
      </svg>
    ),
  },
  {
    text: "下个月签约时机合适吗？",
    icon: (
      <svg {...ICON_PROPS}>
        <rect x="2.5" y="3.5" width="11" height="10" rx="1.5" />
        <path d="M2.5 6.5h11M5.5 2.5v2M10.5 2.5v2" />
      </svg>
    ),
  },
];

/** Empty-session welcome: brand greeting plus clickable starter questions. */
export function SessionWelcome({ onPick }: SessionWelcomeProps) {
  return (
    <div className="welcome">
      <KairosLogo size={60} className="welcome__logo" />
      <h2 className="welcome__title">
        你好，我是 <span className="welcome__brand">Kairos</span>
      </h2>
      <p className="welcome__subtitle">
        告诉我你的出生信息和想了解的问题，我帮你看清局势、把握时机。
      </p>

      <div className="welcome__hint">或者试试这些</div>
      <div className="welcome__grid">
        {STARTERS.map((starter) => (
          <button
            key={starter.text}
            type="button"
            className="welcome__card"
            onClick={() => onPick(starter.text)}
          >
            <span className="welcome__card-icon">{starter.icon}</span>
            <span className="welcome__card-text">{starter.text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
