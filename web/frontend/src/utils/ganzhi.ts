const STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"];
const BRANCHES = [
  "子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥",
];

/** 流年干支 for a calendar year (60-甲子 cycle; 2026 -> 丙午). */
export function liunianGanzhi(year: number): string {
  const s = ((year - 4) % 10 + 10) % 10;
  const b = ((year - 4) % 12 + 12) % 12;
  return STEMS[s] + BRANCHES[b];
}

/** Inclusive list of years in [start, end]. */
export function yearRange(start: number, end: number): number[] {
  const years: number[] = [];
  for (let y = start; y <= end; y += 1) years.push(y);
  return years;
}

// ── 十神 (computed from the day master; matches the engine) ──
const STEM_EL: Record<string, { el: string; yang: boolean }> = {
  甲: { el: "木", yang: true }, 乙: { el: "木", yang: false },
  丙: { el: "火", yang: true }, 丁: { el: "火", yang: false },
  戊: { el: "土", yang: true }, 己: { el: "土", yang: false },
  庚: { el: "金", yang: true }, 辛: { el: "金", yang: false },
  壬: { el: "水", yang: true }, 癸: { el: "水", yang: false },
};
// 地支本气（主气藏干）
const BRANCH_MAIN: Record<string, string> = {
  子: "癸", 丑: "己", 寅: "甲", 卯: "乙", 辰: "戊", 巳: "丙",
  午: "丁", 未: "己", 申: "庚", 酉: "辛", 戌: "戊", 亥: "壬",
};
const GENERATES: Record<string, string> = { 木: "火", 火: "土", 土: "金", 金: "水", 水: "木" };
const CONTROLS: Record<string, string> = { 木: "土", 土: "水", 水: "火", 火: "金", 金: "木" };

export function stemTenGod(dayMaster: string, stem: string): string {
  const dm = STEM_EL[dayMaster];
  const x = STEM_EL[stem];
  if (!dm || !x) return "";
  const same = dm.yang === x.yang;
  if (x.el === dm.el) return same ? "比肩" : "劫财";
  if (GENERATES[dm.el] === x.el) return same ? "食神" : "伤官"; // 我生
  if (GENERATES[x.el] === dm.el) return same ? "偏印" : "正印"; // 生我
  if (CONTROLS[dm.el] === x.el) return same ? "偏财" : "正财"; // 我克
  if (CONTROLS[x.el] === dm.el) return same ? "七杀" : "正官"; // 克我
  return "";
}

export function branchTenGod(dayMaster: string, branch: string): string {
  const main = BRANCH_MAIN[branch];
  return main ? stemTenGod(dayMaster, main) : "";
}

// 地支本五行
const BRANCH_EL: Record<string, string> = {
  子: "水", 丑: "土", 寅: "木", 卯: "木", 辰: "土", 巳: "火",
  午: "火", 未: "土", 申: "金", 酉: "金", 戌: "土", 亥: "水",
};
const EL_CLASS: Record<string, string> = {
  木: "el-wood", 火: "el-fire", 土: "el-earth", 金: "el-metal", 水: "el-water",
};

/** CSS class coloring a 天干/地支 by its 五行. */
export function elementClass(char: string): string {
  const el = STEM_EL[char]?.el ?? BRANCH_EL[char];
  return el ? EL_CLASS[el] : "";
}

/** CSS class coloring a 五行 element NAME (木/火/土/金/水) directly — for views
 *  that already hold the element, not a 干支 char (e.g. the 五行气势 bars). */
export function elementNameClass(el: string): string {
  return EL_CLASS[el] ?? "";
}

/** 流年 ten-gods for a year, relative to the day master. */
export function liunianTenGods(dayMaster: string, year: number): {
  stem: string;
  branch: string;
} {
  const gz = liunianGanzhi(year);
  return {
    stem: stemTenGod(dayMaster, gz[0]),
    branch: branchTenGod(dayMaster, gz[1]),
  };
}
