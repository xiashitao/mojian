import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In a remote sandbox the browser reaches the dev server through a proxied
// HTTPS host, so HMR must dial back over wss to that exact host. Set
// VITE_HMR_HOST to enable it there. Locally (unset) Vite auto-detects the host
// from the page, so HMR just works — no hardcoded sandbox domain to break it.
const hmrHost = process.env.VITE_HMR_HOST;

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: "0.0.0.0",
    hmr: hmrHost ? { host: hmrHost, protocol: "wss" } : undefined,
    proxy: {
      "/api": {
        target: "http://localhost:8010",
        changeOrigin: true,
      },
    },
  },
});
