import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.ALERT_APP_URL;
if (!baseURL || !/^http:\/\/127\.0\.0\.1:\d+$/.test(baseURL) || process.env.ALERT_APP_ISOLATED !== "1") {
  throw new Error("Provide ALERT_APP_URL and ALERT_APP_ISOLATED=1 for a freshly seeded isolated runtime.");
}
export default defineConfig({
  testDir: "./e2e",
  testMatch: "alert-application.spec.ts",
  workers: 1,
  retries: 0,
  timeout: 45_000,
  reporter: "list",
  outputDir: "../output/alert-components-20261102/app-results",
  use: { baseURL, screenshot: "only-on-failure", trace: "retain-on-failure" },
  projects: [{ name: "isolated-alert-app", use: { ...devices["Desktop Chrome"] } }],
});
