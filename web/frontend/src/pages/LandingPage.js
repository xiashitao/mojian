import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import logo from "../assets/logo.png";
import { ThemeSwitcher } from "../theme";
const PLACEHOLDERS = [
    "1990年5月15日早上8点半，北京出生，男，想看事业",
    "我适合创业还是稳定上班？",
    "我想看感情里的相处模式",
    "我的性格优势和短板是什么？",
];
export default function LandingPage() {
    const navigate = useNavigate();
    const [input, setInput] = useState("");
    const [phIndex, setPhIndex] = useState(0);
    useEffect(() => {
        if (input.trim())
            return;
        const id = window.setTimeout(() => setPhIndex((i) => (i + 1) % PLACEHOLDERS.length), 3200);
        return () => window.clearTimeout(id);
    }, [input, phIndex]);
    const handleSubmit = (text) => {
        const t = text.trim() || PLACEHOLDERS[phIndex];
        if (!t)
            return;
        navigate("/session", { state: { initialMessage: t } });
    };
    const handleKeyDown = (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            handleSubmit(input);
        }
    };
    return (_jsxs("div", { className: "oracle landing", children: [_jsx("div", { className: "oracle__grain", "aria-hidden": true }), _jsx("div", { className: "oracle__glow", "aria-hidden": true }), _jsxs("header", { className: "oracle-header oracle-header--landing", children: [_jsxs("div", { className: "oracle-header__brand", children: [_jsx("img", { className: "oracle-header__logo", src: logo, alt: "\u58A8\u9274" }), _jsx("span", { className: "oracle-header__mark", children: "\u58A8\u9274" })] }), _jsxs("nav", { className: "oracle-header__actions", children: [_jsx(ThemeSwitcher, {}), _jsx("button", { type: "button", className: "oracle-header__cta", onClick: () => navigate("/session"), children: "\u5F00\u59CB\u95EE\u8BCA" })] })] }), _jsx("main", { className: "landing__main", children: _jsxs("section", { className: "landing__hero", "aria-labelledby": "landing-title", children: [_jsx("img", { className: "landing__hero-logo", src: logo, alt: "\u58A8\u9274" }), _jsx("div", { className: "oracle-empty__eyebrow", children: "\u95EE\u4E8B\u5165\u76D8 \u00B7 \u89C2\u65F6\u8BC6\u52BF" }), _jsx("h1", { id: "landing-title", className: "oracle-empty__title", children: "\u58A8\u9274" }), _jsx("p", { className: "oracle-empty__text", children: "\u8BF4\u51FA\u751F\u8FB0\u3001\u5730\u70B9\u3001\u6027\u522B\u548C\u6240\u95EE\u4E4B\u4E8B\uFF0C\u6211\u4F1A\u4ECE\u65F6\u95F4\u4E0E\u7ED3\u6784\u51FA\u53D1\uFF0C\u5E2E\u4F60\u770B\u6E05\u5F53\u4E0B\u7684\u8D70\u5411\u4E0E\u9009\u62E9\u8FB9\u754C\u3002" }), _jsxs("form", { className: "landing__composer", onSubmit: (event) => {
                                event.preventDefault();
                                handleSubmit(input);
                            }, children: [_jsxs("div", { className: "landing__input-wrap", children: [!input && (_jsx("span", { className: "landing__placeholder", children: PLACEHOLDERS[phIndex] }, phIndex)), _jsx("input", { className: "composer__input landing__input", value: input, onChange: (e) => setInput(e.target.value), onKeyDown: handleKeyDown, "aria-label": "\u8F93\u5165\u60F3\u54A8\u8BE2\u7684\u95EE\u9898", autoFocus: true })] }), _jsx("button", { type: "submit", className: "landing__send", "aria-label": "\u53D1\u9001", children: "\u2192" })] })] }) })] }));
}
