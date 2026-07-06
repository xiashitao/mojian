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

/** 主体标签:把后端的 subject 枚举翻成中文,让用户一眼看到当前在聊谁。 */
const SUBJECT_LABEL: Record<string, string> = {
  self: "自己",
  spouse: "配偶",
  child: "子女",
  parent: "父母",
  other: "他人",
};

/** Slim strip under the header showing the current topic, birth info, and a
 *  secondary entry point into the full 命盘 detail. */
export function ChatContextBar({ topic, birthInfo, chart }: ChatContextBarProps) {
  const [detailOpen, setDetailOpen] = useState(false);
  const hasBirth = Boolean(
    birthInfo &&
      (birthInfo.birth_date || birthInfo.birth_time || birthInfo.birth_place),
  );

  if (!topic && !hasBirth) return null;

  const subjectLabel = birthInfo?.subject ? SUBJECT_LABEL[birthInfo.subject] ?? null : null;

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
      {subjectLabel && <span className="chat-context__subject">{subjectLabel}</span>}
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
