import type { Interactions } from "../../types/diagnosis";

const TYPE_CLASS: Record<string, string> = {
  gan_he: "he",
  san_he: "he",
  ban_he: "he",
  san_hui: "hui",
  ban_hui: "hui",
  chong: "chong",
  xing: "xing",
  hai: "hai",
};

const TYPE_LABEL: Record<string, string> = {
  gan_he: "干合",
  san_he: "三合",
  ban_he: "半合",
  san_hui: "三会",
  ban_hui: "半会",
  chong: "相冲",
  xing: "相刑",
  hai: "相害",
};

export function InteractionsCard({ interactions }: { interactions: Interactions }) {
  const groups = Object.keys(TYPE_LABEL).filter(
    (k) => interactions[k as keyof Interactions]?.length > 0,
  );

  const totalCount = groups.reduce(
    (sum, k) => sum + (interactions[k as keyof Interactions] as unknown[]).length,
    0,
  );

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">
          BRANCH INTERACTIONS <span className="cn">地支关系</span>
        </div>
        <div className="card-title" style={{ color: "var(--text-muted)" }}>
          {totalCount} INTERACTIONS
        </div>
      </div>
      <div className="card-body">
        {totalCount === 0 ? (
          <div style={{ color: "var(--text-muted)", fontSize: 13, textAlign: "center", padding: 20 }}>
            无明显的刑冲合化关系
          </div>
        ) : (
          <div className="interaction-list">
            {groups.map((key) => {
              const items = interactions[key as keyof Interactions] as Record<
                string,
                unknown
              >[];
              return items.map((item, i) => {
                const kind = item.kind as string || TYPE_LABEL[key];
                const participants = Array.isArray(item.participants)
                  ? (item.participants as string[])
                  : [];
                const elements = Array.isArray(item.elements)
                  ? (item.elements as string[])
                  : [];
                const note = item.note as string || "";
                const resultingEl = item.resulting_element as string || "";

                return (
                  <div key={`${key}-${i}`} className={`interaction-row ${TYPE_CLASS[key]}`}>
                    <div className="interaction-type">{kind || TYPE_LABEL[key]}</div>
                    <div className="interaction-pillars">
                      {participants.length > 0 ? participants.join(" · ") : elements.join(" · ")}
                      {resultingEl && ` → ${resultingEl}`}
                    </div>
                    <div className="interaction-rule" style={{ color: "var(--text-dim)" }}>
                      —
                    </div>
                    <div className="interaction-note">{note}</div>
                  </div>
                );
              });
            })}
          </div>
        )}
      </div>
    </div>
  );
}
