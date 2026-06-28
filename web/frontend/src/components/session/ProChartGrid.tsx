import { Fragment } from "react";
import type { ProColumn } from "../../types/session";
import { elementClass } from "../../utils/ganzhi";

/** 专业细盘网格：流年 · 大运 · 年 · 月 · 日 · 时 并排成一张表，每列从上到下是
 *  主星 / 天干 / 地支 / 藏干 / 星运 / 自坐 / 空亡 / 纳音 / 神煞。天干地支藏干按五行上色。
 *  星运/自坐/神煞 行仅在后端给出对应数据时出现（渐进增强，无数据则不占位）。 */
export function ProChartGrid({
  columns,
  gender,
}: {
  columns: ProColumn[];
  gender?: string | null;
}) {
  if (!columns.length) return null;

  const sepIndex = columns.findIndex((c) => c.label.includes("柱"));
  const hasStarLuck = columns.some((c) => c.star_luck);
  const hasSelfSit = columns.some((c) => c.self_sit);
  const hasShensha = columns.some((c) => (c.shensha?.length ?? 0) > 0);

  // A labeled row = the left rowlabel cell + one cell per column, so the CSS
  // grid keeps every column aligned and auto-sizes each row to its tallest cell.
  const cellClass = (i: number, extra = "") =>
    `prochart__cell${i === sepIndex ? " is-sep" : ""}${
      columns[i].label === "流年" || columns[i].label === "大运" ? " is-now" : ""
    }${extra ? ` ${extra}` : ""}`;

  const mainStar = (c: ProColumn) =>
    c.label === "日柱"
      ? gender === "female"
        ? "元女"
        : "元男"
      : c.stem_ten_god ?? "—";

  return (
    <div
      className="prochart"
      style={{
        gridTemplateColumns: `max-content repeat(${columns.length}, minmax(52px, 1fr))`,
      }}
      role="table"
      aria-label="专业细盘"
    >
      {/* 表头：日期/柱位 */}
      <div className="prochart__rowlabel prochart__rowlabel--head">日期</div>
      {columns.map((c, i) => (
        <div key={`h-${i}`} className={cellClass(i, "prochart__head")}>
          {c.label}
        </div>
      ))}

      {/* 主星 */}
      <div className="prochart__rowlabel">主星</div>
      {columns.map((c, i) => (
        <div key={`god-${i}`} className={cellClass(i, "prochart__god")}>
          {mainStar(c)}
        </div>
      ))}

      {/* 天干 */}
      <div className="prochart__rowlabel">天干</div>
      {columns.map((c, i) => (
        <div key={`stem-${i}`} className={cellClass(i, "prochart__gz")}>
          <b className={elementClass(c.stem)}>{c.stem}</b>
        </div>
      ))}

      {/* 地支 */}
      <div className="prochart__rowlabel">地支</div>
      {columns.map((c, i) => (
        <div key={`branch-${i}`} className={cellClass(i, "prochart__gz")}>
          <b className={elementClass(c.branch)}>{c.branch}</b>
        </div>
      ))}

      {/* 藏干 */}
      <div className="prochart__rowlabel">藏干</div>
      {columns.map((c, i) => (
        <div key={`hidden-${i}`} className={cellClass(i, "prochart__hidden")}>
          {c.hidden.map((h) => (
            <span key={h.char} className="prochart__hid">
              <b className={elementClass(h.char)}>{h.char}</b>
              <i>{h.ten_god}</i>
            </span>
          ))}
        </div>
      ))}

      {/* 星运 (Stage 2) */}
      {hasStarLuck && (
        <Fragment>
          <div className="prochart__rowlabel">星运</div>
          {columns.map((c, i) => (
            <div key={`star-${i}`} className={cellClass(i, "prochart__sub")}>
              {c.star_luck ?? "—"}
            </div>
          ))}
        </Fragment>
      )}

      {/* 自坐 (Stage 2) */}
      {hasSelfSit && (
        <Fragment>
          <div className="prochart__rowlabel">自坐</div>
          {columns.map((c, i) => (
            <div key={`self-${i}`} className={cellClass(i, "prochart__sub")}>
              {c.self_sit ?? "—"}
            </div>
          ))}
        </Fragment>
      )}

      {/* 空亡 */}
      <div className="prochart__rowlabel">空亡</div>
      {columns.map((c, i) => (
        <div key={`void-${i}`} className={cellClass(i, "prochart__sub")}>
          {c.void_branches.join("")}
        </div>
      ))}

      {/* 纳音 */}
      <div className="prochart__rowlabel">纳音</div>
      {columns.map((c, i) => (
        <div key={`nayin-${i}`} className={cellClass(i, "prochart__sub")}>
          {c.nayin ?? "—"}
        </div>
      ))}

      {/* 神煞 (Stage 3) */}
      {hasShensha && (
        <Fragment>
          <div className="prochart__rowlabel">神煞</div>
          {columns.map((c, i) => (
            <div key={`ss-${i}`} className={cellClass(i, "prochart__shensha")}>
              {(c.shensha ?? []).map((s) => (
                <span key={s} className="prochart__ss">
                  {s}
                </span>
              ))}
            </div>
          ))}
        </Fragment>
      )}
    </div>
  );
}
