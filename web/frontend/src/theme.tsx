import { createContext, useContext, useEffect, useMemo, useState } from "react";

export type ThemeMode = "light" | "dark";

type ThemeContextValue = {
  mode: ThemeMode;
  resolvedTheme: ThemeMode;
  setMode: (mode: ThemeMode) => void;
};

const THEME_STORAGE_KEY = "bazibase-theme-mode";
const ThemeContext = createContext<ThemeContextValue | null>(null);

function getInitialMode(): ThemeMode {
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  // First visit: seed from the OS preference once, then it stays a fixed choice.
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>(getInitialMode);

  useEffect(() => {
    window.localStorage.setItem(THEME_STORAGE_KEY, mode);
  }, [mode]);

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = mode;
    root.style.colorScheme = mode;
  }, [mode]);

  const value = useMemo<ThemeContextValue>(
    () => ({ mode, resolvedTheme: mode, setMode }),
    [mode],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const value = useContext(ThemeContext);
  if (!value) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return value;
}

const THEME_LABEL: Record<ThemeMode, string> = {
  light: "浅色模式",
  dark: "深色模式",
};

const ThemeIcon = ({ mode }: { mode: ThemeMode }) => {
  if (mode === "light")
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round">
        <circle cx="8" cy="8" r="3" />
        <line x1="8" y1="1.5" x2="8" y2="3" />
        <line x1="8" y1="13" x2="8" y2="14.5" />
        <line x1="1.5" y1="8" x2="3" y2="8" />
        <line x1="13" y1="8" x2="14.5" y2="8" />
        <line x1="3.4" y1="3.4" x2="4.5" y2="4.5" />
        <line x1="11.5" y1="11.5" x2="12.6" y2="12.6" />
        <line x1="3.4" y1="12.6" x2="4.5" y2="11.5" />
        <line x1="11.5" y1="4.5" x2="12.6" y2="3.4" />
      </svg>
    );
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round">
      <path d="M13.2 10.5A5.5 5.5 0 0 1 5.5 2.8a5.5 5.5 0 1 0 7.7 7.7Z" />
    </svg>
  );
};

export function ThemeSwitcher() {
  const { mode, setMode } = useTheme();

  const toggle = () => setMode(mode === "dark" ? "light" : "dark");

  return (
    <button
      type="button"
      className="theme-toggle-btn"
      onClick={toggle}
      aria-label={`当前主题：${THEME_LABEL[mode]}，点击切换`}
      title={THEME_LABEL[mode]}
    >
      <ThemeIcon mode={mode} />
    </button>
  );
}
