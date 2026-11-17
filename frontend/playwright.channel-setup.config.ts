import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e", testMatch: "channel-setup.spec.ts", workers: 1, timeout: 30000,
  reporter: [["list"], ["json", { outputFile: "../output/channels-fixes-20261114/results.json" }]],
  outputDir: "../output/channels-fixes-20261114/browser",
  use: { baseURL: "http://127.0.0.1:49971", browserName: "chromium", screenshot: "only-on-failure", trace: "retain-on-failure" },
  webServer: { command: "npm run dev -- --host 127.0.0.1 --port 49971", url: "http://127.0.0.1:49971/e2e/fixtures/channel-setup.html", reuseExistingServer: false },
});
