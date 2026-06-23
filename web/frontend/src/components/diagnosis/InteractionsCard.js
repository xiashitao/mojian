import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
const TYPE_CLASS = {
    gan_he: "he",
    san_he: "he",
    ban_he: "he",
    san_hui: "hui",
    ban_hui: "hui",
    chong: "chong",
    xing: "xing",
    hai: "hai",
};
const TYPE_LABEL = {
    gan_he: "干合",
    san_he: "三合",
    ban_he: "半合",
    san_hui: "三会",
    ban_hui: "半会",
    chong: "相冲",
    xing: "相刑",
    hai: "相害",
};
export function InteractionsCard({ interactions }) {
    const groups = Object.keys(TYPE_LABEL).filter((k) => interactions[k]?.length > 0);
    const totalCount = groups.reduce((sum, k) => sum + interactions[k].length, 0);
    return (_jsxs("div", { className: "card", children: [_jsxs("div", { className: "card-header", children: [_jsxs("div", { className: "card-title", children: ["BRANCH INTERACTIONS ", _jsx("span", { className: "cn", children: "\u5730\u652F\u5173\u7CFB" })] }), _jsxs("div", { className: "card-title", style: { color: "var(--text-muted)" }, children: [totalCount, " INTERACTIONS"] })] }), _jsx("div", { className: "card-body", children: totalCount === 0 ? (_jsx("div", { style: { color: "var(--text-muted)", fontSize: 13, textAlign: "center", padding: 20 }, children: "\u65E0\u660E\u663E\u7684\u5211\u51B2\u5408\u5316\u5173\u7CFB" })) : (_jsx("div", { className: "interaction-list", children: groups.map((key) => {
                        const items = interactions[key];
                        return items.map((item, i) => {
                            const kind = item.kind || TYPE_LABEL[key];
                            const participants = Array.isArray(item.participants)
                                ? item.participants
                                : [];
                            const elements = Array.isArray(item.elements)
                                ? item.elements
                                : [];
                            const note = item.note || "";
                            const resultingEl = item.resulting_element || "";
                            return (_jsxs("div", { className: `interaction-row ${TYPE_CLASS[key]}`, children: [_jsx("div", { className: "interaction-type", children: kind || TYPE_LABEL[key] }), _jsxs("div", { className: "interaction-pillars", children: [participants.length > 0 ? participants.join(" · ") : elements.join(" · "), resultingEl && ` → ${resultingEl}`] }), _jsx("div", { className: "interaction-rule", style: { color: "var(--text-dim)" }, children: "\u2014" }), _jsx("div", { className: "interaction-note", children: note })] }, `${key}-${i}`));
                        });
                    }) })) })] }));
}
