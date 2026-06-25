import type { Topic } from "../../types/api";
import type { BirthInfo } from "../../types/session";
import { genderText, topicText } from "../../utils/sessionFormat";

export interface ChatContextBarProps {
  topic: Topic | string | null | undefined;
  birthInfo: BirthInfo | null;
}

/** Slim strip under the header showing the current topic and birth info. */
export function ChatContextBar({ topic, birthInfo }: ChatContextBarProps) {
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
    </div>
  );
}
