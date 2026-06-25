import { useState } from "react";
import type { Topic } from "../../types/api";
import type { BirthInfo, ChartData } from "../../types/session";
import { genderText, topicText } from "../../utils/sessionFormat";
import { ChartDetailModal } from "./ChartDetailModal";

export interface ChatContextBarProps {
  topic: Topic | string | null | undefined;
  birthInfo: BirthInfo | null;
  chart: ChartData | null;
}

/** Slim strip under the header showing the current topic, birth info, and a
 *  secondary entry point into the full 命盘 detail. */
export function ChatContextBar({ topic, birthInfo, chart }: ChatContextBarProps) {
  const [detailOpen, setDetailOpen] = useState(false);
  const hasBirth = Boolean(
    birthInfo &&
      (birthInfo.birth_date || birthInfo.birth_time || birthInfo.birth_place),
  );

  if (!topic && !hasBirth) return null;

  return (
    <div className="chat-context">
      {topic && <span className="chat-context__topic">{topicText(topic)}</span>}
      {hasBirth && birthInfo && (
        <span className="chat-context__birth">
          {[
            birthInfo.birth_date,
            birthInfo.birth_time,
            birthInfo.birth_place,
            genderText(birthInfo.gender),
          ]
            .filter(Boolean)
            .join(" · ")}
        </span>
      )}
      {chart && (
        <button
          type="button"
          className="chat-context__chart"
          onClick={() => setDetailOpen(true)}
          title="查看完整八字、大运与流年"
        >
          查看专业细盘
        </button>
      )}
      {detailOpen && chart && (
        <ChartDetailModal chart={chart} onClose={() => setDetailOpen(false)} />
      )}
    </div>
  );
}
