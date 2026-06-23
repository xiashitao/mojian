import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";
import type { ThemeMode } from "./theme";

const THEME_STORAGE_KEY = "bazibase-theme-mode";

function resolveTheme(mode: ThemeMode): "light" | "dark" {
  if (mode === "light" || mode === "dark") return mode;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
const initialTheme =
  storedTheme === "light" || storedTheme === "dark" || storedTheme === "system"
    ? storedTheme
    : "system";
const resolvedTheme = resolveTheme(initialTheme as ThemeMode);
document.documentElement.dataset.theme = resolvedTheme;
document.documentElement.style.colorScheme = resolvedTheme;

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
