import type { Topic } from "../types/api";

export function topicText(topic: Topic | string | null | undefined): string {
  switch (topic) {
    case "career":
      return "事业";
    case "relationship":
      return "感情";
    case "wealth":
      return "财运";
    case "personality":
      return "性格";
    default:
      return "未定";
  }
}

export function genderText(gender: string | null | undefined): string {
  if (gender === "male") return "男";
  if (gender === "female") return "女";
  return "——";
}

/** "HH:MM" from an ISO timestamp, or "" when absent/invalid. */
export function formatClock(iso?: string): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const hh = String(date.getHours()).padStart(2, "0");
  const mm = String(date.getMinutes()).padStart(2, "0");
  return `${hh}:${mm}`;
}

/** Human-friendly relative time from a SQLite UTC timestamp. */
export function relativeTime(sqliteTs: string | null | undefined): string {
  if (!sqliteTs) return "——";
  const date = new Date(sqliteTs.replace(" ", "T") + "Z");
  if (Number.isNaN(date.getTime())) return "——";

  const diff = Date.now() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes}分前`;
  if (hours < 24) return `${hours}时前`;
  if (days === 1) return "昨日";
  if (days < 7) return `${days}日前`;
  if (date.getFullYear() === new Date().getFullYear()) {
    return `${date.getMonth() + 1}月${date.getDate()}日`;
  }
  return `${date.getFullYear()}.${date.getMonth() + 1}.${date.getDate()}`;
}
