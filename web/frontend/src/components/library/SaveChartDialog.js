import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
export function SaveChartDialog({ input, onSave, onClose }) {
    const [label, setLabel] = useState("");
    const [saving, setSaving] = useState(false);
    const handleSave = async () => {
        setSaving(true);
        try {
            await onSave(label || `${input.date} ${input.gender === "male" ? "男" : "女"}`);
            onClose();
        }
        finally {
            setSaving(false);
        }
    };
    return (_jsx("div", { style: {
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 50,
        }, onClick: onClose, children: _jsxs("div", { style: {
                background: "var(--bg-panel)",
                border: "1px solid var(--border-default)",
                borderRadius: 8,
                padding: 24,
                width: 400,
                maxWidth: "90vw",
            }, onClick: (e) => e.stopPropagation(), children: [_jsx("h3", { style: { fontSize: 16, fontWeight: 600, marginBottom: 16, color: "var(--text-primary)" }, children: "\u4FDD\u5B58\u547D\u4F8B" }), _jsxs("div", { style: { marginBottom: 16 }, children: [_jsx("input", { type: "text", value: label, onChange: (e) => setLabel(e.target.value), placeholder: "\u547D\u4F8B\u540D\u79F0\uFF08\u5982\uFF1A\u5F20\u4E09\uFF09", autoFocus: true, style: {
                                width: "100%",
                                background: "var(--bg-card)",
                                border: "1px solid var(--border-default)",
                                borderRadius: 4,
                                padding: "8px 12px",
                                color: "var(--text-primary)",
                                fontSize: 14,
                                fontFamily: "var(--font-cn)",
                                outline: "none",
                            } }), _jsxs("div", { style: {
                                fontSize: 11,
                                color: "var(--text-muted)",
                                marginTop: 8,
                                fontFamily: "var(--font-mono)",
                            }, children: [input.date, " ", input.time, " \u00B7 ", input.gender === "male" ? "男" : "女", " \u00B7", " ", input.longitude, "\u00B0E"] })] }), _jsxs("div", { style: { display: "flex", gap: 8, justifyContent: "flex-end" }, children: [_jsx("button", { className: "btn btn-secondary", onClick: onClose, children: "\u53D6\u6D88" }), _jsx("button", { className: "btn btn-primary", onClick: handleSave, disabled: saving, children: saving ? "保存中…" : "保存" })] })] }) }));
}
