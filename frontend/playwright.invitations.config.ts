import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

export default defineConfig({
  ...base,
  testMatch: /pilot-invitations\.spec\.ts/,
  timeout: 60_000,
  webServer: [
    { command: `"${process.env.E2E_PYTHON}" ../scripts/invitation_browser_runtime.py`,
      url: `${process.env.E2E_API_BASE_URL}/health/`, reuseExistingServer: false, timeout: 120_000 },
    { command: `npm run dev -- --host 127.0.0.1 --port ${process.env.E2E_FRONTEND_PORT} --strictPort`,
      url: process.env.E2E_BASE_URL, reuseExistingServer: false, timeout: 120_000 },
  ],
});
