import { Fragment } from "react";
import type { ElementWeight } from "../../types/session";
import { elementNameClass } from "../../utils/ganzhi";

/** 五行气势 bars laid out along the 相生 cycle (木→火→土→金→水). Bar height
 *  encodes each element's weight; the left-to-right read shows 气势流通. */
export function ElementFlow({ elements }: { elements: ElementWeight[] }) {
  const max = Math.max(...elements.map((e) => e.count), 1);

  return (
    <div className="el-flow">
      {elements.map((e, i) => (
        <Fragment key={e.el}>
          {i > 0 && <span className="el-flow__arrow">→</span>}
          <div className="el-flow__item">
            <span className="el-flow__track">
              <span
                className={`el-flow__bar ${elementNameClass(e.el)}`}
                style={{ height: `${(e.count / max) * 100}%` }}
              />
            </span>
            <span className={`el-flow__name ${elementNameClass(e.el)}`}>{e.el}</span>
            <span className="el-flow__pct">{e.pct}%</span>
          </div>
        </Fragment>
      ))}
    </div>
  );
}
