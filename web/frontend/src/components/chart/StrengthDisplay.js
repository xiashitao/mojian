import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { elClass } from "../../utils/format";
export function StrengthDisplay({ strength, dayMaster, dayMasterElement, }) {
    const verdict = strength.verdict;
    const verdictTag = verdict === "身强"
        ? "tag-good"
        : verdict === "身弱"
            ? "tag-bad"
            : "tag-neutral";
    // Map score to a 0-100 position for the meter
    // Typical scores range from 0 to ~50; we'll map proportionally
    const meterPct = Math.min((strength.total_score / 50) * 100, 100);
    return (_jsxs("div", { className: "card", children: [_jsx("div", { className: "card-header", children: _jsxs("div", { className: "card-title", children: ["STRENGTH ", _jsx("span", { className: "cn", children: "\u65E5\u5E72\u65FA\u8870" })] }) }), _jsxs("div", { className: "card-body", children: [_jsxs("div", { className: "strength-score", children: [_jsx("div", { className: `strength-value ${elClass(dayMaster)}`, children: dayMaster }), _jsxs("div", { children: [_jsxs("div", { className: "strength-label", children: [verdict, strength.borderline && (_jsx("span", { className: "tag tag-neutral", style: { marginLeft: 6 }, children: "\u4E34\u754C" }))] }), _jsxs("div", { style: { fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-muted)" }, children: ["\u8BC4\u5206: ", strength.total_score, " \u00B7 ", dayMasterElement, "\u547D"] })] })] }), _jsx("div", { className: "strength-meter", children: _jsxs("div", { className: "strength-track", children: [_jsx("div", { className: "strength-tick", style: { left: "20%" } }), _jsx("div", { className: "strength-tick", style: { left: "40%" } }), _jsx("div", { className: "strength-tick", style: { left: "50%" } }), _jsx("div", { className: "strength-tick", style: { left: "60%" } }), _jsx("div", { className: "strength-tick", style: { left: "80%" } }), _jsx("div", { className: "strength-marker", style: { left: `${meterPct}%` }, children: _jsx("span", { className: "strength-marker-value", children: strength.total_score }) })] }) }), _jsxs("div", { className: "strength-scale", children: [_jsx("span", { children: "\u6781\u5F31" }), _jsx("span", { children: "\u504F\u5F31" }), _jsx("span", { children: "\u4E2D\u548C" }), _jsx("span", { children: "\u504F\u65FA" }), _jsx("span", { children: "\u6781\u65FA" })] }), strength.breakdown.length > 0 && (_jsx("div", { className: "strength-breakdown", children: strength.breakdown.map((b, i) => (_jsxs("div", { className: "strength-item", children: [_jsx("div", { className: "strength-item-label", children: b.source }), _jsxs("div", { className: "strength-item-value", children: ["+", b.contribution, " \u00B7 ", b.note] })] }, i))) }))] })] }));
}
