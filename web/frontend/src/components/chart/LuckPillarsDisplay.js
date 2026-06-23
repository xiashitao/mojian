import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { elClass } from "../../utils/format";
const STEM_BRANCH_SEQ = [
    "甲子", "乙丑", "丙寅", "丁卯", "戊辰", "己巳", "庚午", "辛未", "壬申", "癸酉",
    "甲戌", "乙亥", "丙子", "丁丑", "戊寅", "己卯", "庚辰", "辛巳", "壬午", "癸未",
    "甲申", "乙酉", "丙戌", "丁亥", "戊子", "己丑", "庚寅", "辛卯", "壬辰", "癸巳",
    "甲午", "乙未", "丙申", "丁酉", "戊戌", "己亥", "庚子", "辛丑", "壬寅", "癸卯",
    "甲辰", "乙巳", "丙午", "丁未", "戊申", "己酉", "庚戌", "辛亥", "壬子", "癸丑",
    "甲寅", "乙卯", "丙辰", "丁巳", "戊午", "己未", "庚申", "辛酉", "壬戌", "癸亥",
];
function getStemBranchForYear(year) {
    // 1984 is 甲子 year (year index 0 in the 60-cycle)
    const idx = ((year - 1984) % 60 + 60) % 60;
    return STEM_BRANCH_SEQ[idx];
}
export function LuckPillarsDisplay({ luck }) {
    const { direction, start_age, pillars } = luck;
    const startStr = `${start_age.years}岁${start_age.months > 0 ? start_age.months + "月" : ""}`;
    // Determine current phase based on current year
    const currentYear = new Date().getFullYear();
    const currentPhaseIdx = pillars.findIndex((p) => currentYear >= p.start_year && currentYear <= p.end_year);
    const [activeIdx, setActiveIdx] = useState(currentPhaseIdx >= 0 ? currentPhaseIdx : 0);
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
    return (_jsxs("div", { className: "card", children: [_jsxs("div", { className: "card-header", children: [_jsxs("div", { className: "card-title", children: ["LUCK PILLARS ", _jsx("span", { className: "cn", children: "\u5927\u8FD0 \u00B7 \u6D41\u5E74" })] }), _jsxs("div", { className: "card-title", style: { color: "var(--text-muted)" }, children: ["\u8D77\u8FD0: ", startStr, " \u00B7 ", direction, "\u884C"] })] }), _jsxs("div", { style: { padding: "12px 8px" }, children: [_jsx("div", { className: "luck-timeline", children: pillars.map((p, idx) => {
                            const stemChar = p.stem_branch[0];
                            const branchChar = p.stem_branch[1];
                            const isCurrent = idx === currentPhaseIdx;
                            const isActive = idx === activeIdx;
                            return (_jsxs("div", { className: `luck-phase ${isActive ? "active" : ""} ${isCurrent ? "current" : ""}`, onClick: () => setActiveIdx(idx), children: [_jsxs("div", { className: "luck-age", children: [p.start_age, "-", p.end_age] }), _jsxs("div", { className: "luck-ganzhi", children: [_jsx("span", { className: elClass(stemChar), children: stemChar }), _jsx("span", { className: elClass(branchChar), children: branchChar })] }), _jsxs("div", { className: "luck-ten-god", children: [p.stem_ten_god || "—", " \u00B7 ", p.branch_ten_god || "—"] }), _jsxs("div", { className: "luck-relation", children: [p.stem_relative || "—", " \u00B7 ", p.branch_relative || "—"] }), _jsxs("div", { className: "luck-year", children: [p.start_year, "+"] })] }, p.index));
                        }) }), activePillar && (_jsx("div", { className: "luck-detail-years", children: flowYears.map((fy) => (_jsxs("div", { className: "luck-year-cell", children: [_jsx("div", { className: "yr-num", children: fy.year }), _jsxs("div", { className: "yr-gz", children: [_jsx("span", { className: elClass(fy.stem), children: fy.stem }), _jsx("span", { className: elClass(fy.branch), children: fy.branch })] }), _jsxs("div", { className: "yr-age", children: [fy.age, "\u5C81"] })] }, fy.year))) }))] })] }));
}
