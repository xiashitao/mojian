import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { CaseCard } from "./CaseCard";
export function ArbitrationPanel({ result, loading }) {
    if (loading) {
        return (_jsxs("div", { className: "empty-state", children: [_jsx("div", { className: "empty-state-icon", children: "\u23F3" }), _jsx("p", { style: { fontSize: 14 }, children: "\u6B63\u5728\u8C03\u7528 DeepSeek \u4EF2\u88C1\uFF0C\u8BF7\u7A0D\u5019\u2026" })] }));
    }
    if (!result) {
        return (_jsxs("div", { className: "empty-state", children: [_jsx("div", { className: "empty-state-icon", children: "\u2696" }), _jsx("p", { style: { fontSize: 14 }, children: "\u6392\u76D8\u540E\u70B9\u51FB\u300C\u89E6\u53D1 LLM \u4EF2\u88C1\u300D\u6309\u94AE\u5F00\u59CB\u5206\u6790" })] }));
    }
    const { summary } = result;
    return (_jsxs("div", { children: [_jsxs("div", { style: {
                    display: "flex",
                    alignItems: "center",
                    gap: 16,
                    marginBottom: 16,
                    padding: "10px 16px",
                    background: "var(--bg-panel)",
                    border: "1px solid var(--border-default)",
                    borderRadius: 8,
                }, children: [_jsxs("span", { style: { fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-muted)" }, children: ["\u5DF2\u89E3\u51B3: ", _jsx("span", { style: { color: "var(--accent-green)", fontWeight: 600 }, children: summary.resolved })] }), _jsxs("span", { style: { fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-muted)" }, children: ["\u672A\u89E3\u51B3: ", _jsx("span", { style: { color: "var(--accent-amber)", fontWeight: 600 }, children: summary.unresolved })] }), _jsxs("span", { style: { fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-muted)" }, children: ["\u9519\u8BEF: ", _jsx("span", { style: { color: "var(--accent-red)", fontWeight: 600 }, children: summary.errors })] }), _jsxs("span", { style: { fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-muted)", marginLeft: "auto" }, children: ["\u603B\u8BA1: ", summary.total] })] }), result.cases.length === 0 ? (_jsxs("div", { className: "empty-state", children: [_jsx("div", { className: "empty-state-icon", children: "\u2713" }), _jsx("p", { style: { fontSize: 14 }, children: "\u65E0\u4E89\u8BAE\u70B9\uFF0C\u8BCA\u65AD\u4E00\u81F4\u3002" })] })) : (result.cases.map((c) => (_jsx(CaseCard, { caseItem: c, response: result.responses[c.case_id], error: result.errors[c.case_id] }, c.case_id))))] }));
}
