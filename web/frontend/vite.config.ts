import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: "0.0.0.0",
    hmr: {
      host: "cdfc69-sandbox-session6ac8c435d5f8414aa1-5173.agent.alibaba-inc.com",
      protocol: "wss",
    },
    proxy: {
      "/api": {
        target: "http://localhost:8010",
        changeOrigin: true,
      },
    },
  },
});
