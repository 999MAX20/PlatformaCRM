import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.RECORDS_TOOLBAR_URL;
if (!baseURL || !/^http:\/\/127\.0\.0\.1:\d+$/.test(baseURL) || process.env.RECORDS_TOOLBAR_ISOLATED !== "1") throw new Error("Isolated Records toolbar runtime required");
export default defineConfig({
  testDir: "./e2e", testMatch: ["records-toolbar.spec.ts", "records-bell-recovery.spec.ts"], workers: 1, retries: 0,
  timeout: 90_000, reporter: "list", outputDir: "../output/records-toolbar-20261103/browser-results",
  use: { baseURL, screenshot: "only-on-failure", trace: "retain-on-failure" },
  projects: [{ name: "records-toolbar", use: { ...devices["Desktop Chrome"] } }],
});
