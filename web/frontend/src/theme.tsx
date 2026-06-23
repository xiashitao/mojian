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

export function ThemeSwitcher() {
  const { mode, setMode } = useTheme();

  return (
    <div className="theme-switch" role="group" aria-label="主题切换">
      <button
        type="button"
        className={`theme-switch__item ${mode === "light" ? "is-active" : ""}`}
        aria-pressed={mode === "light"}
        onClick={() => setMode("light")}
      >
        浅色
      </button>
      <button
        type="button"
        className={`theme-switch__item ${mode === "system" ? "is-active" : ""}`}
        aria-pressed={mode === "system"}
        onClick={() => setMode("system")}
      >
        跟随
      </button>
      <button
        type="button"
        className={`theme-switch__item ${mode === "dark" ? "is-active" : ""}`}
        aria-pressed={mode === "dark"}
        onClick={() => setMode("dark")}
      >
        深色
      </button>
    </div>
  );
}
