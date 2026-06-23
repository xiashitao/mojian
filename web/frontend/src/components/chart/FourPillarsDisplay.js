import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { elClass, bgClass } from "../../utils/format";
const QI_LABEL = {
    本气: "主",
    中气: "中",
    余气: "余",
};
export function FourPillarsDisplay({ fourPillars, voidInfo, }) {
    // Traditional order: time → day → month → year (right to left)
    const positions = ["hour", "day", "month", "year"];
    const headers = {
        hour: { en: "HOUR", cn: "时柱" },
        day: { en: "DAY", cn: "日柱" },
        month: { en: "MONTH", cn: "月柱" },
        year: { en: "YEAR", cn: "年柱" },
    };
    return (_jsxs("div", { className: "card", children: [_jsx("div", { className: "card-header", children: _jsxs("div", { className: "card-title", children: ["FOUR PILLARS ", _jsx("span", { className: "cn", children: "\u56DB\u67F1\u6392\u76D8" })] }) }), _jsxs("div", { style: { padding: "8px 12px" }, children: [_jsxs("div", { className: "pillars-container", children: [_jsx("div", { className: "pillar-cell label", children: "POSITION" }), positions.map((pos) => (_jsx("div", { className: "pillar-cell", children: _jsxs("div", { className: "pillar-header", children: [headers[pos].en, _jsx("span", { className: "cn", children: headers[pos].cn })] }) }, pos))), _jsx("div", { className: "pillar-cell rlabel", children: "\u8BF4\u660E" }), _jsx("div", { className: "pillar-cell label", children: "TEN GOD" }), positions.map((pos) => {
                                const p = fourPillars[pos];
                                return (_jsx("div", { className: `pillar-cell pillar-col ${pos === "day" ? "day" : ""}`, children: _jsx("span", { className: `pillar-sub ${pos === "day" ? "daymaster" : ""}`, children: p.stem.ten_god }) }, pos));
                            }), _jsx("div", { className: "pillar-cell rlabel", children: "\u5929\u5E72\u5341\u795E" }), _jsx("div", { className: "pillar-cell label", children: "RELATIVE" }), positions.map((pos) => {
                                const p = fourPillars[pos];
                                return (_jsx("div", { className: `pillar-cell pillar-col ${pos === "day" ? "day" : ""}`, children: _jsx("span", { className: "pillar-sub relation", children: pos === "day" ? "自身" : p.stem.relative || "—" }) }, pos));
                            }), _jsx("div", { className: "pillar-cell rlabel", children: "\u5929\u5E72\u516D\u4EB2" }), _jsx("div", { className: "pillar-cell label", children: "STEM" }), positions.map((pos) => {
                                const p = fourPillars[pos];
                                return (_jsx("div", { className: `pillar-cell pillar-col ${pos === "day" ? "day" : ""} ${bgClass(p.stem.char)}`, children: _jsx("span", { className: `stem ${elClass(p.stem.char)}`, children: p.stem.char }) }, pos));
                            }), _jsx("div", { className: "pillar-cell rlabel", children: "\u5929\u5E72" }), _jsx("div", { className: "pillar-cell label", children: "BRANCH" }), positions.map((pos) => {
                                const p = fourPillars[pos];
                                return (_jsx("div", { className: `pillar-cell pillar-col ${pos === "day" ? "day" : ""} ${bgClass(p.branch.char)}`, children: _jsx("span", { className: `branch ${elClass(p.branch.char)} ${p.branch_is_void ? "pillar-void active" : ""}`, children: p.branch.char }) }, pos));
                            }), _jsx("div", { className: "pillar-cell rlabel", children: "\u5730\u652F" }), _jsx("div", { className: "pillar-cell label", children: "B. GOD" }), positions.map((pos) => {
                                const p = fourPillars[pos];
                                return (_jsx("div", { className: `pillar-cell pillar-col ${pos === "day" ? "day" : ""}`, children: _jsx("span", { className: "pillar-sub", children: p.branch.ten_god }) }, pos));
                            }), _jsx("div", { className: "pillar-cell rlabel", children: "\u5730\u652F\u5341\u795E" }), _jsx("div", { className: "pillar-cell label", children: "B. RELATIVE" }), positions.map((pos) => {
                                const p = fourPillars[pos];
                                return (_jsx("div", { className: `pillar-cell pillar-col ${pos === "day" ? "day" : ""}`, children: _jsx("span", { className: "pillar-sub relation", children: pos === "day" ? "自身" : p.branch.relative || "—" }) }, pos));
                            }), _jsx("div", { className: "pillar-cell rlabel", children: "\u5730\u652F\u516D\u4EB2" }), _jsx("div", { className: "pillar-cell label", children: "HIDDEN" }), positions.map((pos) => {
                                const p = fourPillars[pos];
                                return (_jsx("div", { className: `pillar-cell pillar-col ${pos === "day" ? "day" : ""}`, children: _jsx("span", { className: "hidden-stems", children: p.branch.hidden_stems.map((hs, i) => (_jsxs("span", { className: elClass(hs.char), children: [hs.char, _jsx("span", { className: "qi", children: QI_LABEL[hs.role] || hs.role[0] })] }, i))) }) }, pos));
                            }), _jsx("div", { className: "pillar-cell rlabel", children: "\u85CF\u5E72" }), _jsx("div", { className: "pillar-cell label", children: "NAYIN" }), positions.map((pos) => {
                                const p = fourPillars[pos];
                                return (_jsx("div", { className: `pillar-cell pillar-col ${pos === "day" ? "day" : ""}`, children: _jsx("span", { className: "pillar-nayin", children: p.nayin || "—" }) }, pos));
                            }), _jsx("div", { className: "pillar-cell rlabel", children: "\u7EB3\u97F3" }), _jsx("div", { className: "pillar-cell label", children: "VOID" }), positions.map((pos) => {
                                const p = fourPillars[pos];
                                return (_jsx("div", { className: `pillar-cell pillar-col ${pos === "day" ? "day" : ""}`, children: _jsx("span", { className: `pillar-void ${p.branch_is_void ? "active" : ""}`, children: p.branch_is_void ? "空" : "—" }) }, pos));
                            }), _jsx("div", { className: "pillar-cell rlabel", children: "\u7A7A\u4EA1" })] }), voidInfo && (_jsx("div", { className: "pillars-footer", children: _jsx("span", { style: { fontFamily: "var(--font-mono)", color: "var(--text-muted)" }, children: Object.entries(voidInfo).map(([pos, branches]) => (_jsxs("span", { children: [" ", pos === "day" ? "日" : pos === "year" ? "年" : pos === "month" ? "月" : "时", "\u7A7A: ", branches.join(""), "  |  "] }, pos))) }) }))] })] }));
}
