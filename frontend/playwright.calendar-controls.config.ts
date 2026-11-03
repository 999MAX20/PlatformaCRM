import { defineConfig, devices } from "@playwright/test";
const port = process.env.CALENDAR_TEST_PORT || "57433";
const baseURL = `http://127.0.0.1:${port}`;
export default defineConfig({
  testDir: "./e2e", testMatch: "calendar-controls.spec.ts", workers: 1, retries: 0,
  timeout: 30_000, expect: { timeout: 5_000 }, reporter: "list",
  outputDir: "../output/calendar-shared-20261103/browser-results",
  use: { baseURL, screenshot: "only-on-failure", trace: "retain-on-failure" },
  webServer: { command: `node node_modules/vite/bin/vite.js --host 127.0.0.1 --port ${port} --strictPort`, url: baseURL, reuseExistingServer: false, env: { E2E_API_BASE_URL: "http://127.0.0.1:9" } },
  projects: [{ name: "calendar-chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1000 } } }],
});
