import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.RECORDS_BELL_URL;
if (!baseURL || !/^http:\/\/127\.0\.0\.1:\d+$/.test(baseURL) || process.env.RECORDS_BELL_ISOLATED !== "1") {
  throw new Error("Provide RECORDS_BELL_URL and RECORDS_BELL_ISOLATED=1 for an isolated fixture runtime.");
}
export default defineConfig({
  testDir: "./e2e", testMatch: ["records-bell-recovery.spec.ts", "service-s03.spec.ts"], workers: 1, retries: 0,
  timeout: 90_000, reporter: "list", outputDir: "../output/records-bell-fix-20261103/browser-results",
  use: { baseURL, screenshot: "only-on-failure", trace: "retain-on-failure" },
  projects: [{ name: "records-bell", use: { ...devices["Desktop Chrome"] } }],
});
