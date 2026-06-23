import type { FourPillars } from "../../types/chart";
import { elClass, bgClass } from "../../utils/format";

interface FourPillarsDisplayProps {
  fourPillars: FourPillars;
  voidInfo?: Record<string, string[]>;
}

const QI_LABEL: Record<string, string> = {
  本气: "主",
  中气: "中",
  余气: "余",
};

export function FourPillarsDisplay({
  fourPillars,
  voidInfo,
}: FourPillarsDisplayProps) {
  // Traditional order: time → day → month → year (right to left)
  const positions = ["hour", "day", "month", "year"] as const;
  const headers: Record<string, { en: string; cn: string }> = {
    hour: { en: "HOUR", cn: "时柱" },
    day: { en: "DAY", cn: "日柱" },
    month: { en: "MONTH", cn: "月柱" },
    year: { en: "YEAR", cn: "年柱" },
  };

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">
          FOUR PILLARS <span className="cn">四柱排盘</span>
        </div>
      </div>
      <div style={{ padding: "8px 12px" }}>
        <div className="pillars-container">
          {/* Row: Headers */}
          <div className="pillar-cell label">POSITION</div>
          {positions.map((pos) => (
            <div key={pos} className="pillar-cell">
              <div className="pillar-header">
                {headers[pos].en}
                <span className="cn">{headers[pos].cn}</span>
              </div>
            </div>
          ))}
          <div className="pillar-cell rlabel">说明</div>

          {/* Row: 天干十神 */}
          <div className="pillar-cell label">TEN GOD</div>
          {positions.map((pos) => {
            const p = fourPillars[pos];
            return (
              <div key={pos} className={`pillar-cell pillar-col ${pos === "day" ? "day" : ""}`}>
                <span className={`pillar-sub ${pos === "day" ? "daymaster" : ""}`}>
                  {p.stem.ten_god}
                </span>
              </div>
            );
          })}
          <div className="pillar-cell rlabel">天干十神</div>

          {/* Row: 天干六亲 */}
          <div className="pillar-cell label">RELATIVE</div>
          {positions.map((pos) => {
            const p = fourPillars[pos];
            return (
              <div key={pos} className={`pillar-cell pillar-col ${pos === "day" ? "day" : ""}`}>
                <span className="pillar-sub relation">
                  {pos === "day" ? "自身" : p.stem.relative || "—"}
                </span>
              </div>
            );
          })}
          <div className="pillar-cell rlabel">天干六亲</div>

          {/* Row: 天干 */}
          <div className="pillar-cell label">STEM</div>
          {positions.map((pos) => {
            const p = fourPillars[pos];
            return (
              <div key={pos} className={`pillar-cell pillar-col ${pos === "day" ? "day" : ""} ${bgClass(p.stem.char)}`}>
                <span className={`stem ${elClass(p.stem.char)}`}>{p.stem.char}</span>
              </div>
            );
          })}
          <div className="pillar-cell rlabel">天干</div>

          {/* Row: 地支 */}
          <div className="pillar-cell label">BRANCH</div>
          {positions.map((pos) => {
            const p = fourPillars[pos];
            return (
              <div key={pos} className={`pillar-cell pillar-col ${pos === "day" ? "day" : ""} ${bgClass(p.branch.char)}`}>
                <span className={`branch ${elClass(p.branch.char)} ${p.branch_is_void ? "pillar-void active" : ""}`}>
                  {p.branch.char}
                </span>
              </div>
            );
          })}
          <div className="pillar-cell rlabel">地支</div>

          {/* Row: 地支十神 */}
          <div className="pillar-cell label">B. GOD</div>
          {positions.map((pos) => {
            const p = fourPillars[pos];
            return (
              <div key={pos} className={`pillar-cell pillar-col ${pos === "day" ? "day" : ""}`}>
                <span className="pillar-sub">{p.branch.ten_god}</span>
              </div>
            );
          })}
          <div className="pillar-cell rlabel">地支十神</div>

          {/* Row: 地支六亲 */}
          <div className="pillar-cell label">B. RELATIVE</div>
          {positions.map((pos) => {
            const p = fourPillars[pos];
            return (
              <div key={pos} className={`pillar-cell pillar-col ${pos === "day" ? "day" : ""}`}>
                <span className="pillar-sub relation">
                  {pos === "day" ? "自身" : p.branch.relative || "—"}
                </span>
              </div>
            );
          })}
          <div className="pillar-cell rlabel">地支六亲</div>

          {/* Row: 藏干 */}
          <div className="pillar-cell label">HIDDEN</div>
          {positions.map((pos) => {
            const p = fourPillars[pos];
            return (
              <div key={pos} className={`pillar-cell pillar-col ${pos === "day" ? "day" : ""}`}>
                <span className="hidden-stems">
                  {p.branch.hidden_stems.map((hs, i) => (
                    <span key={i} className={elClass(hs.char)}>
                      {hs.char}
                      <span className="qi">{QI_LABEL[hs.role] || hs.role[0]}</span>
                    </span>
                  ))}
                </span>
              </div>
            );
          })}
          <div className="pillar-cell rlabel">藏干</div>

          {/* Row: 纳音 */}
          <div className="pillar-cell label">NAYIN</div>
          {positions.map((pos) => {
            const p = fourPillars[pos];
            return (
              <div key={pos} className={`pillar-cell pillar-col ${pos === "day" ? "day" : ""}`}>
                <span className="pillar-nayin">{p.nayin || "—"}</span>
              </div>
            );
          })}
          <div className="pillar-cell rlabel">纳音</div>

          {/* Row: 空亡 */}
          <div className="pillar-cell label">VOID</div>
          {positions.map((pos) => {
            const p = fourPillars[pos];
            return (
              <div key={pos} className={`pillar-cell pillar-col ${pos === "day" ? "day" : ""}`}>
                <span className={`pillar-void ${p.branch_is_void ? "active" : ""}`}>
                  {p.branch_is_void ? "空" : "—"}
                </span>
              </div>
            );
          })}
          <div className="pillar-cell rlabel">空亡</div>
        </div>

        {/* Footer with void info */}
        {voidInfo && (
          <div className="pillars-footer">
            <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
              {Object.entries(voidInfo).map(([pos, branches]) => (
                <span key={pos}>
                  {" "}{pos === "day" ? "日" : pos === "year" ? "年" : pos === "month" ? "月" : "时"}空: {branches.join("")}
                  {"  |  "}
                </span>
              ))}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
