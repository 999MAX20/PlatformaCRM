import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: /(?:page-loading|inbox-compact|inbox-draft-provenance|inbox-inspector|dashboard-data-loading)\.spec\.ts/,
  timeout: 90_000,
  expect: { timeout: 12_000 },
  workers: 1,
  retries: 0,
  reporter: "list",
  outputDir: "../output/page-loading-20261113/browser",
  use: {
    baseURL: process.env.E2E_BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1536, height: 960 } } }],
});
