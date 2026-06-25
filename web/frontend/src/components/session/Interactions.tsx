import type { ChartInteraction, InteractionGroup } from "../../types/session";
import { elementClass } from "../../utils/ganzhi";

const GROUP_CLASS: Record<InteractionGroup, string> = {
  合: "is-he",
  冲: "is-chong",
  刑: "is-xing",
  害: "is-hai",
};

/** Grouped 刑冲合害 list — the structural relationships between the four 地支
 *  (and 天干合), each pillar pair colored by its 五行. */
export function Interactions({ interactions }: { interactions: ChartInteraction[] }) {
  if (interactions.length === 0) {
    return <p className="interactions__empty">四柱之间无明显刑冲合害</p>;
  }

  return (
    <ul className="interactions">
      {interactions.map((it) => (
        <li
          key={`${it.group}-${it.chars.join("")}-${it.kind}`}
          className={`interaction ${GROUP_CLASS[it.group]}`}
        >
          <span className="interaction__group">{it.group}</span>
          <span className="interaction__chars">
            {it.chars.map((c, j) => (
              <span key={j} className={elementClass(c)}>
                {c}
              </span>
            ))}
          </span>
          <span className="interaction__kind">{it.kind}</span>
          {it.positions.length > 0 && (
            <span className="interaction__pos">{it.positions.join("·")}</span>
          )}
          {it.note && <span className="interaction__note">{it.note}</span>}
        </li>
      ))}
    </ul>
  );
}
