import { useEffect, useRef, useState } from "react";
import type { ChartData } from "../../types/session";
import {
  elementClass,
  liunianGanzhi,
  liunianTenGods,
  yearRange,
} from "../../utils/ganzhi";
import { Ganzhi } from "./Ganzhi";
import { Interactions } from "./Interactions";
import { ProChartGrid } from "./ProChartGrid";

interface Props {
  chart: ChartData;
  onClose: () => void;
}

/** Full chart detail: 八字 + 大运 + per-year 流年, current year highlighted. */
export function ChartDetailModal({ chart, onClose }: Props) {
  const currentYear = chart.current?.year;
  const currentLuck = chart.current?.luck_index;
  const dialogRef = useRef<HTMLDivElement>(null);

  // The pro grid's 流年/大运 columns follow a selected period (defaults to now).
  // Clicking a 大运 or 流年 in the timeline re-points them; the natal 4 stay put.
  const luckPillars = chart.luck.pillars;
  const [selLuckIdx, setSelLuckIdx] = useState(currentLuck ? currentLuck - 1 : 0);
  const [selYear, setSelYear] = useState<number | undefined>(currentYear);

  const selLuck = luckPillars[selLuckIdx];
  const selLiunianCol = selLuck?.years?.find((y) => y.year === selYear)?.column;
  const selLuckCol = selLuck?.column;
  const natalCols = chart.columns?.slice(2) ?? [];
  const gridColumns =
    selLiunianCol && selLuckCol
      ? [selLiunianCol, selLuckCol, ...natalCols]
      : chart.columns ?? [];

  const selectLuck = (i: number) => {
    setSelLuckIdx(i);
    const lp = luckPillars[i];
    // Keep the year if it falls inside this 大运, else jump to its first 流年.
    if (!lp || selYear === undefined || selYear < lp.start_year || selYear > lp.end_year) {
      setSelYear(lp?.start_year);
    }
  };
  const selectYear = (i: number, y: number) => {
    setSelLuckIdx(i);
    setSelYear(y);
  };
  const onActivate = (fn: () => void) => (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fn();
    }
  };

  // Mirror the AuthModal conventions: Escape closes, the dialog takes focus on
  // open (so keyboard + screen readers land inside it), and the page behind is
  // scroll-locked while it's up.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    dialogRef.current?.focus();
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [onClose]);

  return (
    <div className="detail-scrim" onClick={onClose}>
      <div
        className="detail-modal"
        role="dialog"
        aria-modal="true"
        aria-label="完整命盘"
        tabIndex={-1}
        ref={dialogRef}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="detail-modal__head">
          <span className="detail-modal__title">完整命盘</span>
          <button
            type="button"
            className="detail-modal__close"
            onClick={onClose}
            aria-label="关闭"
          >
            ✕
          </button>
        </div>

        <div className="detail-modal__body">
          <section className="detail-section">
            <h4 className="detail-section__h">命盘 · 流年大运并参</h4>
            {chart.columns && chart.columns.length > 0 ? (
              <div className="prochart-wrap">
                <ProChartGrid columns={gridColumns} gender={chart.birth?.gender} />
              </div>
            ) : (
            <div className="detail-bazi">
              {chart.pillars.map((p) => (
                <div
                  key={p.label}
                  className={`detail-pillar ${p.label === "日柱" ? "is-day" : ""}`}
                >
                  <span className="detail-pillar__label">{p.label}</span>
                  <span className="detail-pillar__god">{p.stem_ten_god ?? "—"}</span>
                  <span className={`detail-pillar__gz ${elementClass(p.stem)}`}>
                    {p.stem}
                  </span>
                  <span className={`detail-pillar__gz ${elementClass(p.branch)}`}>
                    {p.branch}
                  </span>
                  <span className="detail-pillar__god">{p.branch_ten_god ?? "—"}</span>
                  <span className="detail-pillar__hidden">
                    {(p.hidden ?? []).map((h) => (
                      <span key={h.char} className="hidden-stem">
                        <b className={elementClass(h.char)}>{h.char}</b>
                        {h.role && <i className="hidden-stem__role">{h.role[0]}</i>}
                        {h.ten_god ?? ""}
                      </span>
                    ))}
                  </span>
                  <span className="detail-pillar__nayin">{p.nayin}</span>
                </div>
              ))}
            </div>
            )}
          </section>

          <section className="detail-section">
            <h4 className="detail-section__h">
              大运 · 流年
              {chart.luck.direction ? `（${chart.luck.direction}行）` : ""}
            </h4>
            <div className="detail-luck">
              {chart.luck.pillars.map((lp, i) => (
                <div
                  key={`${lp.stem_branch}-${lp.start_year}`}
                  className={`dayun ${currentLuck === i + 1 ? "is-current" : ""} ${
                    i === selLuckIdx ? "is-selected" : ""
                  }`}
                >
                  <div
                    className="dayun__head"
                    role="button"
                    tabIndex={0}
                    aria-pressed={i === selLuckIdx}
                    onClick={() => selectLuck(i)}
                    onKeyDown={onActivate(() => selectLuck(i))}
                  >
                    <span className="dayun__gz">
                      <Ganzhi gz={lp.stem_branch} />
                    </span>
                    <span className="dayun__meta">
                      {lp.start_age}–{lp.end_age}岁 · {lp.start_year}–{lp.end_year}
                    </span>
                    {lp.stem_ten_god && (
                      <span className="dayun__god">
                        {lp.stem_ten_god}/{lp.branch_ten_god}
                      </span>
                    )}
                  </div>
                  <div className="dayun__years">
                    {yearRange(lp.start_year, lp.end_year).map((y) => {
                      const tg = liunianTenGods(chart.day_master, y);
                      const isSel = i === selLuckIdx && y === selYear;
                      return (
                        <span
                          key={y}
                          className={`liunian-cell ${y === currentYear ? "is-now" : ""} ${
                            isSel ? "is-selected" : ""
                          }`}
                          role="button"
                          tabIndex={0}
                          aria-pressed={isSel}
                          onClick={() => selectYear(i, y)}
                          onKeyDown={onActivate(() => selectYear(i, y))}
                        >
                          <span className="liunian-cell__y">{y}</span>
                          <span className="liunian-cell__gz">
                            <Ganzhi gz={liunianGanzhi(y)} />
                          </span>
                          <span className="liunian-cell__tg">
                            {tg.stem} {tg.branch}
                          </span>
                        </span>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="detail-section">
            <h4 className="detail-section__h">刑冲合害</h4>
            <Interactions interactions={chart.interactions ?? []} />
          </section>
        </div>
      </div>
    </div>
  );
}
