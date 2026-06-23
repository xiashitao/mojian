import type { Strength } from "../../types/chart";
import { elClass } from "../../utils/format";

interface StrengthDisplayProps {
  strength: Strength;
  dayMaster: string;
  dayMasterElement: string;
}

export function StrengthDisplay({
  strength,
  dayMaster,
  dayMasterElement,
}: StrengthDisplayProps) {
  const verdict = strength.verdict;
  const verdictTag =
    verdict === "身强"
      ? "tag-good"
      : verdict === "身弱"
        ? "tag-bad"
        : "tag-neutral";

  // Map score to a 0-100 position for the meter
  // Typical scores range from 0 to ~50; we'll map proportionally
  const meterPct = Math.min((strength.total_score / 50) * 100, 100);

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">
          STRENGTH <span className="cn">日干旺衰</span>
        </div>
      </div>
      <div className="card-body">
        <div className="strength-score">
          <div className={`strength-value ${elClass(dayMaster)}`}>
            {dayMaster}
          </div>
          <div>
            <div className="strength-label">
              {verdict}
              {strength.borderline && (
                <span className="tag tag-neutral" style={{ marginLeft: 6 }}>临界</span>
              )}
            </div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-muted)" }}>
              评分: {strength.total_score} · {dayMasterElement}命
            </div>
          </div>
        </div>

        {/* Meter */}
        <div className="strength-meter">
          <div className="strength-track">
            <div className="strength-tick" style={{ left: "20%" }} />
            <div className="strength-tick" style={{ left: "40%" }} />
            <div className="strength-tick" style={{ left: "50%" }} />
            <div className="strength-tick" style={{ left: "60%" }} />
            <div className="strength-tick" style={{ left: "80%" }} />
            <div className="strength-marker" style={{ left: `${meterPct}%` }}>
              <span className="strength-marker-value">{strength.total_score}</span>
            </div>
          </div>
        </div>
        <div className="strength-scale">
          <span>极弱</span>
          <span>偏弱</span>
          <span>中和</span>
          <span>偏旺</span>
          <span>极旺</span>
        </div>

        {/* Breakdown */}
        {strength.breakdown.length > 0 && (
          <div className="strength-breakdown">
            {strength.breakdown.map((b, i) => (
              <div key={i} className="strength-item">
                <div className="strength-item-label">{b.source}</div>
                <div className="strength-item-value">
                  +{b.contribution} · {b.note}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
