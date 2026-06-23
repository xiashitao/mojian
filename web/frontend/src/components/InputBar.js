import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
export function InputBar({ onSubmit, loading, onSave, canSave }) {
    const handleSubmit = (e) => {
        e.preventDefault();
        const form = new FormData(e.target);
        onSubmit({
            date: form.get("date"),
            time: form.get("time"),
            longitude: parseFloat(form.get("longitude")),
            gender: form.get("gender"),
            tz_offset_hours: parseFloat(form.get("tz")),
            apply_solar_time_correction: true,
        });
    };
    return (_jsxs("form", { className: "input-bar", onSubmit: handleSubmit, children: [_jsxs("div", { className: "input-field", children: [_jsx("label", { children: "DATE" }), _jsx("input", { name: "date", type: "date", defaultValue: "1985-03-15" })] }), _jsxs("div", { className: "input-field", children: [_jsx("label", { children: "TIME" }), _jsx("input", { name: "time", type: "time", defaultValue: "10:30" })] }), _jsxs("div", { className: "input-field", children: [_jsx("label", { children: "LON" }), _jsx("input", { name: "longitude", type: "number", step: "0.1", defaultValue: "116.4" })] }), _jsxs("div", { className: "input-field", children: [_jsx("label", { children: "GENDER" }), _jsxs("select", { name: "gender", defaultValue: "male", children: [_jsx("option", { value: "male", children: "\u7537" }), _jsx("option", { value: "female", children: "\u5973" })] })] }), _jsxs("div", { className: "input-field", children: [_jsx("label", { children: "TZ OFFSET" }), _jsx("input", { name: "tz", type: "number", step: "0.5", defaultValue: "8" })] }), _jsx("button", { type: "submit", className: "btn btn-primary", disabled: loading, children: loading ? "排盘中…" : "排 盘" }), _jsx("button", { type: "button", className: "btn btn-secondary", onClick: onSave, disabled: !canSave, children: "\u4FDD\u5B58\u547D\u4F8B" })] }));
}
