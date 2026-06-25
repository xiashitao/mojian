import type { ChartData } from "../../types/session";
import {
  elementClass,
  liunianGanzhi,
  liunianTenGods,
  yearRange,
} from "../../utils/ganzhi";
import { Ganzhi } from "./Ganzhi";

interface Props {
  chart: ChartData;
  onClose: () => void;
}

/** Full chart detail: 八字 + 大运 + per-year 流年, current year highlighted. */
export function ChartDetailModal({ chart, onClose }: Props) {
  const currentYear = chart.current?.year;
  const currentLuck = chart.current?.luck_index;

  return (
    <div className="detail-scrim" onClick={onClose}>
      <div className="detail-modal" onClick={(e) => e.stopPropagation()}>
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
            <h4 className="detail-section__h">八字</h4>
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
                    {p.hidden.map((h) => (
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
                  className={`dayun ${currentLuck === i + 1 ? "is-current" : ""}`}
                >
                  <div className="dayun__head">
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
                      return (
                        <span
                          key={y}
                          className={`liunian-cell ${y === currentYear ? "is-now" : ""}`}
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
        </div>
      </div>
    </div>
  );
}
