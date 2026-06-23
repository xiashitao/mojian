import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
const THEME_STORAGE_KEY = "bazibase-theme-mode";
const ThemeContext = createContext(null);
function getSystemPrefersDark() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
}
function resolveTheme(mode, systemPrefersDark) {
    if (mode === "system") {
        return systemPrefersDark ? "dark" : "light";
    }
    return mode;
}
export function ThemeProvider({ children }) {
    const [mode, setMode] = useState(() => {
        const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
        return stored === "light" || stored === "dark" || stored === "system"
            ? stored
            : "system";
    });
    const [systemPrefersDark, setSystemPrefersDark] = useState(getSystemPrefersDark);
    useEffect(() => {
        const media = window.matchMedia("(prefers-color-scheme: dark)");
        const handleChange = () => setSystemPrefersDark(media.matches);
        handleChange();
        media.addEventListener("change", handleChange);
        return () => media.removeEventListener("change", handleChange);
    }, []);
    const resolvedTheme = resolveTheme(mode, systemPrefersDark);
    useEffect(() => {
        window.localStorage.setItem(THEME_STORAGE_KEY, mode);
    }, [mode]);
    useEffect(() => {
        const root = document.documentElement;
        root.dataset.theme = resolvedTheme;
        root.style.colorScheme = resolvedTheme;
    }, [resolvedTheme]);
    const value = useMemo(() => ({ mode, resolvedTheme, setMode }), [mode, resolvedTheme]);
    return _jsx(ThemeContext.Provider, { value: value, children: children });
}
export function useTheme() {
    const value = useContext(ThemeContext);
    if (!value) {
        throw new Error("useTheme must be used within ThemeProvider");
    }
    return value;
}
export function ThemeSwitcher() {
    const { mode, setMode } = useTheme();
    return (_jsxs("div", { className: "theme-switch", role: "group", "aria-label": "\u4E3B\u9898\u5207\u6362", children: [_jsx("button", { type: "button", className: `theme-switch__item ${mode === "light" ? "is-active" : ""}`, "aria-pressed": mode === "light", onClick: () => setMode("light"), children: "\u6D45\u8272" }), _jsx("button", { type: "button", className: `theme-switch__item ${mode === "system" ? "is-active" : ""}`, "aria-pressed": mode === "system", onClick: () => setMode("system"), children: "\u8DDF\u968F" }), _jsx("button", { type: "button", className: `theme-switch__item ${mode === "dark" ? "is-active" : ""}`, "aria-pressed": mode === "dark", onClick: () => setMode("dark"), children: "\u6DF1\u8272" })] }));
}
