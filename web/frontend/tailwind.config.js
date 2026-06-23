/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: {
          base: "#0a0e1a",
          panel: "#111827",
          card: "#161e2e",
          hover: "#1e293b",
        },
        accent: {
          cyan: "#06b6d4",
          blue: "#3b82f6",
        },
        el: {
          wood: "#4ade80",
          fire: "#f87171",
          earth: "#facc15",
          metal: "#cbd5e1",
          water: "#60a5fa",
        },
      },
      fontFamily: {
        serif: ['"Noto Serif SC"', '"Songti SC"', "serif"],
        mono: ['"JetBrains Mono"', '"SF Mono"', "monospace"],
      },
    },
  },
  plugins: [],
};
