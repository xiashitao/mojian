import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
const CATEGORY_CLASS = {
    rescue: "case-rescue",
    conflict: "case-conflict",
};
function getConfidenceColor(confidence) {
    if (confidence >= 0.75)
        return "var(--accent-green)";
    if (confidence >= 0.5)
        return "var(--accent-amber)";
    return "var(--accent-red)";
}
export function CaseCard({ caseItem, response, error }) {
    const catClass = CATEGORY_CLASS[caseItem.category] || "case-rescue";
    return (_jsxs("div", { className: "case-card", children: [_jsxs("div", { className: "case-header", children: [_jsx("span", { className: `case-category ${catClass}`, children: caseItem.category.toUpperCase() }), _jsx("span", { className: "case-title", children: caseItem.title }), _jsx("span", { className: `case-status ${error ? "fail" : response ? "ok" : "pending"}`, children: error ? "FAIL" : response ? "OK" : "..." })] }), _jsxs("div", { className: "case-body", children: [_jsx("p", { style: { fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }, children: caseItem.description }), caseItem.options.length > 0 && (_jsx("div", { style: { display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }, children: caseItem.options.map((opt) => (_jsx("span", { style: {
                                fontSize: 10,
                                fontFamily: "var(--font-mono)",
                                color: "var(--text-muted)",
                                background: "var(--bg-elevated)",
                                padding: "2px 6px",
                                borderRadius: 3,
                            }, children: opt }, opt))) })), error && (_jsx("div", { className: "case-response", children: _jsxs("p", { style: { fontSize: 12, color: "var(--accent-red)" }, children: ["\u4EF2\u88C1\u5931\u8D25\uFF1A", error] }) })), response && (_jsxs("div", { className: "case-response", children: [_jsxs("div", { className: "response-decision", children: [_jsx("span", { className: "response-decision-text", children: response.decision }), _jsx("div", { className: "confidence-bar", children: _jsx("div", { className: "confidence-fill", style: {
                                                width: `${response.confidence * 100}%`,
                                                background: getConfidenceColor(response.confidence),
                                            } }) }), _jsxs("span", { className: "confidence-value", style: { color: getConfidenceColor(response.confidence) }, children: [(response.confidence * 100).toFixed(0), "%"] }), response.is_unresolved && (_jsx("span", { style: {
                                            fontSize: 9,
                                            fontFamily: "var(--font-mono)",
                                            color: "var(--accent-amber)",
                                            background: "rgba(245,158,11,0.15)",
                                            padding: "1px 6px",
                                            borderRadius: 3,
                                        }, children: "UNRESOLVED" }))] }), _jsx("div", { className: "response-reasoning", children: response.reasoning }), response.cited_rules.length > 0 && (_jsx("div", { className: "response-rules", children: response.cited_rules.map((rule, i) => (_jsx("span", { className: "response-rule-chip", children: rule }, i))) }))] }))] })] }));
}
