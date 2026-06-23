import type { ElementDistribution } from "../../types/chart";
import { getElementHex } from "../../utils/format";

interface ElementDonutChartProps {
  distribution: ElementDistribution;
  total: number;
}

const ELEMENT_ORDER = ["木", "火", "土", "金", "水"];

export function ElementDonutChart({
  distribution,
  total,
}: ElementDonutChartProps) {
  const entries = ELEMENT_ORDER.filter((el) => distribution[el]).map((el) => ({
    name: el,
    count: distribution[el].count,
    percentage: distribution[el].percentage,
    color: getElementHex(el),
  }));

  const radius = 90;
  const strokeWidth = 34;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">
          ELEMENT DISTRIBUTION <span className="cn">五行力量分布</span>
        </div>
        <div className="card-title" style={{ color: "var(--text-muted)" }}>
          TOTAL: {total} COUNTS
        </div>
      </div>
      <div className="element-dist-card-body">
        {/* Donut chart */}
        <div style={{ position: "relative", flexShrink: 0 }}>
          <svg width={200} height={200} viewBox="0 0 240 240">
            <circle cx="120" cy="120" r={radius} fill="none" stroke="var(--bg-elevated)" strokeWidth={strokeWidth} />
            {entries.map((entry) => {
              const dash = (entry.count / total) * circumference;
              const segment = (
                <circle
                  key={entry.name}
                  cx="120"
                  cy="120"
                  r={radius}
                  fill="none"
                  stroke={entry.color}
                  strokeWidth={strokeWidth}
                  strokeDasharray={`${dash} ${circumference - dash}`}
                  strokeDashoffset={-offset}
                  transform="rotate(-90 120 120)"
                />
              );
              offset += dash;
              return segment;
            })}
          </svg>
          <div className="element-donut-center">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 28, fontWeight: 700, color: "var(--text-primary)" }}>
              {total}
            </div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-muted)", letterSpacing: 1 }}>
              COUNTS
            </div>
          </div>
        </div>
        {/* Legend */}
        <div className="element-legend">
          {entries.map((entry) => (
            <div key={entry.name} className="element-legend-row">
              <span className="element-legend-dot" style={{ background: entry.color }} />
              <span className="element-legend-name">{entry.name}</span>
              <span className="element-legend-count">{entry.count} / {total}</span>
              <div className="element-legend-bar">
                <div
                  className="element-legend-fill"
                  style={{ width: `${entry.percentage}%`, background: entry.color }}
                />
              </div>
              <span className="element-legend-pct" style={{ color: entry.color }}>
                {entry.percentage}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
