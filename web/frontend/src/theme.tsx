import { createContext, useContext, useEffect, useMemo, useState } from "react";

export type ThemeMode = "system" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";

type ThemeContextValue = {
  mode: ThemeMode;
  resolvedTheme: ResolvedTheme;
  setMode: (mode: ThemeMode) => void;
};

const THEME_STORAGE_KEY = "bazibase-theme-mode";
const ThemeContext = createContext<ThemeContextValue | null>(null);

function getSystemPrefersDark(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function resolveTheme(mode: ThemeMode, systemPrefersDark: boolean): ResolvedTheme {
  if (mode === "system") {
    return systemPrefersDark ? "dark" : "light";
  }
  return mode;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>(() => {
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

  const value = useMemo<ThemeContextValue>(
    () => ({ mode, resolvedTheme, setMode }),
    [mode, resolvedTheme],
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

const THEME_CYCLE: ThemeMode[] = ["system", "light", "dark"];
const THEME_LABEL: Record<ThemeMode, string> = {
  system: "跟随系统",
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
  if (mode === "dark")
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round">
        <path d="M13.2 10.5A5.5 5.5 0 0 1 5.5 2.8a5.5 5.5 0 1 0 7.7 7.7Z" />
      </svg>
    );
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round">
      <circle cx="8" cy="8" r="3" />
      <path d="M8 5V2.5" />
      <path d="M8 13.5V11" />
      <path d="M5 8H2.5" />
      <path d="M13.5 8H11" />
      <path d="M8 5a3 3 0 0 1 3 3H8Z" fill="currentColor" opacity="0.4" stroke="none" />
    </svg>
  );
};

export function ThemeSwitcher() {
  const { mode, setMode } = useTheme();

  const next = () => {
    const i = THEME_CYCLE.indexOf(mode);
    setMode(THEME_CYCLE[(i + 1) % THEME_CYCLE.length]);
  };

  return (
    <button
      type="button"
      className="theme-toggle-btn"
      onClick={next}
      aria-label={`当前主题：${THEME_LABEL[mode]}，点击切换`}
      title={THEME_LABEL[mode]}
    >
      <ThemeIcon mode={mode} />
    </button>
  );
}
