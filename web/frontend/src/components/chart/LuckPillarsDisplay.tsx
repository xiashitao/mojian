import { useState } from "react";
import type { Luck, LuckPillar } from "../../types/chart";
import { elClass } from "../../utils/format";

interface LuckPillarsDisplayProps {
  luck: Luck;
}

const STEM_BRANCH_SEQ = [
  "甲子","乙丑","丙寅","丁卯","戊辰","己巳","庚午","辛未","壬申","癸酉",
  "甲戌","乙亥","丙子","丁丑","戊寅","己卯","庚辰","辛巳","壬午","癸未",
  "甲申","乙酉","丙戌","丁亥","戊子","己丑","庚寅","辛卯","壬辰","癸巳",
  "甲午","乙未","丙申","丁酉","戊戌","己亥","庚子","辛丑","壬寅","癸卯",
  "甲辰","乙巳","丙午","丁未","戊申","己酉","庚戌","辛亥","壬子","癸丑",
  "甲寅","乙卯","丙辰","丁巳","戊午","己未","庚申","辛酉","壬戌","癸亥",
];

function getStemBranchForYear(year: number): string {
  // 1984 is 甲子 year (year index 0 in the 60-cycle)
  const idx = ((year - 1984) % 60 + 60) % 60;
  return STEM_BRANCH_SEQ[idx];
}

export function LuckPillarsDisplay({ luck }: LuckPillarsDisplayProps) {
  const { direction, start_age, pillars } = luck;
  const startStr = `${start_age.years}岁${start_age.months > 0 ? start_age.months + "月" : ""}`;

  // Determine current phase based on current year
  const currentYear = new Date().getFullYear();
  const currentPhaseIdx = pillars.findIndex(
    (p) => currentYear >= p.start_year && currentYear <= p.end_year,
  );

  const [activeIdx, setActiveIdx] = useState(
    currentPhaseIdx >= 0 ? currentPhaseIdx : 0,
  );
  const activePillar = pillars[activeIdx];

  // Generate flow years for the active pillar
  const flowYears = activePillar
    ? Array.from({ length: activePillar.end_year - activePillar.start_year + 1 }, (_, i) => {
        const yr = activePillar.start_year + i;
        const sb = getStemBranchForYear(yr);
        return {
          year: yr,
          age: activePillar.start_age + i,
          stem: sb[0],
          branch: sb[1],
        };
      })
    : [];

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">
          LUCK PILLARS <span className="cn">大运 · 流年</span>
        </div>
        <div className="card-title" style={{ color: "var(--text-muted)" }}>
          起运: {startStr} · {direction}行
        </div>
      </div>
      <div style={{ padding: "12px 8px" }}>
        <div className="luck-timeline">
          {pillars.map((p, idx) => {
            const stemChar = p.stem_branch[0];
            const branchChar = p.stem_branch[1];
            const isCurrent = idx === currentPhaseIdx;
            const isActive = idx === activeIdx;
            return (
              <div
                key={p.index}
                className={`luck-phase ${isActive ? "active" : ""} ${isCurrent ? "current" : ""}`}
                onClick={() => setActiveIdx(idx)}
              >
                <div className="luck-age">{p.start_age}-{p.end_age}</div>
                <div className="luck-ganzhi">
                  <span className={elClass(stemChar)}>{stemChar}</span>
                  <span className={elClass(branchChar)}>{branchChar}</span>
                </div>
                <div className="luck-ten-god">
                  {p.stem_ten_god || "—"} · {p.branch_ten_god || "—"}
                </div>
                <div className="luck-relation">
                  {p.stem_relative || "—"} · {p.branch_relative || "—"}
                </div>
                <div className="luck-year">{p.start_year}+</div>
              </div>
            );
          })}
        </div>

        {/* Flow years for active phase */}
        {activePillar && (
          <div className="luck-detail-years">
            {flowYears.map((fy) => (
              <div key={fy.year} className="luck-year-cell">
                <div className="yr-num">{fy.year}</div>
                <div className="yr-gz">
                  <span className={elClass(fy.stem)}>{fy.stem}</span>
                  <span className={elClass(fy.branch)}>{fy.branch}</span>
                </div>
                <div className="yr-age">{fy.age}岁</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
