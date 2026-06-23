import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { getElementHex } from "../../utils/format";
const ELEMENT_ORDER = ["木", "火", "土", "金", "水"];
export function ElementDonutChart({ distribution, total, }) {
    const entries = ELEMENT_ORDER.filter((el) => distribution[el]).map((el) => ({
        name: el,
        count: distribution[el].count,
        percentage: distribution[el].percentage,
        color: getElementHex(el),
    }));
    const radius = 90;
    const strokeWidth = 34;
    const circumference = 2 * Math.PI * radius;
    let offset = 0;
    return (_jsxs("div", { className: "card", children: [_jsxs("div", { className: "card-header", children: [_jsxs("div", { className: "card-title", children: ["ELEMENT DISTRIBUTION ", _jsx("span", { className: "cn", children: "\u4E94\u884C\u529B\u91CF\u5206\u5E03" })] }), _jsxs("div", { className: "card-title", style: { color: "var(--text-muted)" }, children: ["TOTAL: ", total, " COUNTS"] })] }), _jsxs("div", { className: "element-dist-card-body", children: [_jsxs("div", { style: { position: "relative", flexShrink: 0 }, children: [_jsxs("svg", { width: 200, height: 200, viewBox: "0 0 240 240", children: [_jsx("circle", { cx: "120", cy: "120", r: radius, fill: "none", stroke: "var(--bg-elevated)", strokeWidth: strokeWidth }), entries.map((entry) => {
                                        const dash = (entry.count / total) * circumference;
                                        const segment = (_jsx("circle", { cx: "120", cy: "120", r: radius, fill: "none", stroke: entry.color, strokeWidth: strokeWidth, strokeDasharray: `${dash} ${circumference - dash}`, strokeDashoffset: -offset, transform: "rotate(-90 120 120)" }, entry.name));
                                        offset += dash;
                                        return segment;
                                    })] }), _jsxs("div", { className: "element-donut-center", children: [_jsx("div", { style: { fontFamily: "var(--font-mono)", fontSize: 28, fontWeight: 700, color: "var(--text-primary)" }, children: total }), _jsx("div", { style: { fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-muted)", letterSpacing: 1 }, children: "COUNTS" })] })] }), _jsx("div", { className: "element-legend", children: entries.map((entry) => (_jsxs("div", { className: "element-legend-row", children: [_jsx("span", { className: "element-legend-dot", style: { background: entry.color } }), _jsx("span", { className: "element-legend-name", children: entry.name }), _jsxs("span", { className: "element-legend-count", children: [entry.count, " / ", total] }), _jsx("div", { className: "element-legend-bar", children: _jsx("div", { className: "element-legend-fill", style: { width: `${entry.percentage}%`, background: entry.color } }) }), _jsxs("span", { className: "element-legend-pct", style: { color: entry.color }, children: [entry.percentage, "%"] })] }, entry.name))) })] })] }));
}
