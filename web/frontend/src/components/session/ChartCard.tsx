import { useRef, useState } from "react";
import { toPng } from "html-to-image";
import type { ChartData } from "../../types/session";

function genderCn(gender: string | null): string {
  if (gender === "male") return "男";
  if (gender === "female") return "女";
  return "";
}

/** Visual 命盘 card (八字 + 大运 + 当前流年), exportable to PNG. */
export function ChartCard({ chart }: { chart: ChartData }) {
  const captureRef = useRef<HTMLDivElement>(null);
  const [exporting, setExporting] = useState(false);
  const current = chart.current;

  const handleExport = async () => {
    const node = captureRef.current;
    if (!node) return;
    setExporting(true);
    try {
      const dataUrl = await toPng(node, {
        pixelRatio: 2,
        backgroundColor: getComputedStyle(node).backgroundColor,
      });
      const link = document.createElement("a");
      link.download = `命盘_${chart.birth.date ?? "chart"}.png`;
      link.href = dataUrl;
      link.click();
    } finally {
      setExporting(false);
    }
  };

  const birthLine = [
    chart.birth.date,
    chart.birth.time,
    chart.birth.place,
    genderCn(chart.birth.gender),
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="chart-card">
      <div className="chart-card__capture" ref={captureRef}>
        <div className="chart-card__head">
          <span className="chart-card__title">命盘</span>
          <span className="chart-card__dm">
            日主 {chart.day_master}
            {chart.day_master_element}
          </span>
        </div>
        {birthLine && <div className="chart-card__birth">{birthLine}</div>}

        <div className="bazi-grid">
          {chart.pillars.map((p) => (
            <div
              key={p.label}
              className={`bazi-col ${p.label === "日柱" ? "is-day" : ""}`}
            >
              <span className="bazi-col__label">{p.label}</span>
              <span className="bazi-col__god">{p.stem_ten_god ?? "—"}</span>
              <span className="bazi-col__stem">{p.stem}</span>
              <span className="bazi-col__branch">{p.branch}</span>
              <span className="bazi-col__hidden">{p.hidden.join(" ")}</span>
              <span className="bazi-col__nayin">{p.nayin}</span>
            </div>
          ))}
        </div>

        <div className="luck">
          <div className="luck__label">
            大运{chart.luck.direction ? `（${chart.luck.direction}行）` : ""}
          </div>
          <div className="luck__track">
            {chart.luck.pillars.map((lp, i) => (
              <div
                key={`${lp.stem_branch}-${lp.start_year}`}
                className={`luck-step ${
                  current && i + 1 === current.luck_index ? "is-current" : ""
                }`}
              >
                <span className="luck-step__gz">{lp.stem_branch}</span>
                <span className="luck-step__year">{lp.start_year}</span>
                <span className="luck-step__age">{lp.start_age}岁</span>
              </div>
            ))}
          </div>
        </div>

        {current && (
          <div className="liunian">
            <span className="liunian__label">流年</span>
            <span className="liunian__gz">{current.liunian}</span>
            <span className="liunian__meta">
              {current.year}年 · {current.nominal_age}岁
              {current.liunian_stem_ten_god
                ? ` · ${current.liunian_stem_ten_god}/${current.liunian_branch_ten_god}`
                : ""}
            </span>
          </div>
        )}
      </div>

      <button
        type="button"
        className="chart-card__export"
        onClick={() => void handleExport()}
        disabled={exporting}
      >
        {exporting ? "导出中…" : "导出命盘图"}
      </button>
    </div>
  );
}
