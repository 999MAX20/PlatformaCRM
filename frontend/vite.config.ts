import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { crmLanding } from "./landing/plugin";
import { randomUUID } from "node:crypto";

const apiProxyTarget =
  process.env.E2E_API_BASE_URL || "http://localhost:8000";

export default defineConfig({
  plugins: [
    crmLanding(),
    {
      name: "app-cache-isolation",
      config(config, { command, mode }) {
        const port = config.server?.port ?? 5173;
        const scope = command === "serve" ? `serve-${port || randomUUID()}` : "build";
        // Concurrent dev/test servers must never replace each other's React optimizer files.
        return {
          cacheDir: `node_modules/.vite/app-${scope}-${encodeURIComponent(mode)}`,
          server: { strictPort: true },
        };
      },
    },
    react(),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          const normalizedId = id.replace(/\\/g, "/");
          if (normalizedId.includes("node_modules/react") || normalizedId.includes("node_modules/react-dom") || normalizedId.includes("node_modules/react-router")) return "react";
          if (normalizedId.includes("node_modules/@tanstack/react-query") || normalizedId.includes("node_modules/axios")) return "query";
          if (normalizedId.includes("node_modules/framer-motion")) return "motion";
          if (normalizedId.includes("node_modules/@dnd-kit")) return "dnd";
          if (normalizedId.includes("node_modules/react-hook-form") || normalizedId.includes("node_modules/@hookform/resolvers") || normalizedId.includes("node_modules/zod")) return "forms";
          if (normalizedId.includes("/src/lib/i18n.tsx")) return "i18n";
          if (normalizedId.includes("/src/components/layout/GlobalSearch.tsx")) return "layout-search";
          if (normalizedId.includes("/src/components/layout/CommandPalette.tsx")) return "command-palette";
          if (normalizedId.includes("/src/components/layout/PlatformLayout.tsx")) return "platform-layout";
          if (
            normalizedId.includes("/src/components/layout/AppLayout.tsx") ||
            normalizedId.includes("/src/components/layout/Header.tsx") ||
            normalizedId.includes("/src/components/layout/MobileNav.tsx") ||
            normalizedId.includes("/src/components/layout/Sidebar.tsx") ||
            normalizedId.includes("/src/components/layout/LanguageSelector.tsx") ||
            normalizedId.includes("/src/components/layout/PageHeaderContext.tsx")
          ) return "app-shell";
          return undefined;
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/ready/": {
        target: apiProxyTarget,
        changeOrigin: true,
      },
      "/api": {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
});
