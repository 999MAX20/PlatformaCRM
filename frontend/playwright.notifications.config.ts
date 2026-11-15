import { defineConfig, devices } from "@playwright/test";

const djangoPort = process.env.E2E_DJANGO_PORT;
const frontendPort = process.env.E2E_FRONTEND_PORT;
if (process.env.ZANI_QUALITY_GATE !== "1" || !djangoPort || !frontendPort) {
  throw new Error("Notification acceptance requires scripts.codex_verify.isolated_runtime");
}
const baseURL = `http://127.0.0.1:${frontendPort}`;

export default defineConfig({
  testDir: "./e2e",
  testMatch: ["notifications-redesign.spec.ts", "notification-refactor.spec.ts"],
  timeout: 30000,
  expect: { timeout: 8000 },
  workers: 1,
  retries: 0,
  reporter: "list",
  outputDir: "../output/notifications-redesign-20261114/browser-final",
  use: { baseURL, trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [{ name: "desktop-chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    { command: "node e2e/django-e2e.mjs serve", url: `http://127.0.0.1:${djangoPort}/health/`, reuseExistingServer: false, timeout: 180000 },
    { command: `npm run preview -- --host 127.0.0.1 --port ${frontendPort} --strictPort`, url: baseURL, reuseExistingServer: false, timeout: 120000 },
  ],
});
