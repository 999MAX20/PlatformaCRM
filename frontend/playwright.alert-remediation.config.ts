import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.ALERT_APP_URL;
if (!baseURL || !/^http:\/\/127\.0\.0\.1:\d+$/.test(baseURL) || process.env.ALERT_APP_ISOLATED !== "1") {
  throw new Error("Provide ALERT_APP_URL and ALERT_APP_ISOLATED=1 for an isolated fixture runtime.");
}
export default defineConfig({
  testDir: "./e2e", testMatch: "alert-remediation.spec.ts", workers: 1, retries: 0,
  timeout: 60_000, reporter: "list",
  outputDir: "../output/alert-remediation-20261103/browser-results",
  use: { baseURL, screenshot: "only-on-failure", trace: "retain-on-failure" },
  projects: [{ name: "isolated-alert-remediation", use: { ...devices["Desktop Chrome"] } }],
});
