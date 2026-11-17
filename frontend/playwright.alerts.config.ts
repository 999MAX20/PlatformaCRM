import { defineConfig, devices } from "@playwright/test";

const port = process.env.ALERT_TEST_PORT || "56930";
const baseURL = `http://127.0.0.1:${port}`;
export default defineConfig({
  testDir: "./e2e",
  testMatch: ["alert-components.spec.ts", "alert-motion.spec.ts", "integration-alerts.spec.ts", "state-behavior.spec.ts"],
  timeout: 30_000,
  expect: { timeout: 5_000 },
  workers: 1,
  retries: 0,
  reporter: "list",
  outputDir: "../output/alert-components-20261102/browser-results",
  use: { baseURL, screenshot: "only-on-failure", trace: "retain-on-failure" },
  webServer: {
    command: `node node_modules/vite/bin/vite.js --host 127.0.0.1 --port ${port} --strictPort`,
    url: baseURL,
    reuseExistingServer: false,
    env: { E2E_API_BASE_URL: "http://127.0.0.1:9" },
  },
  projects: [{ name: "alerts-chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1000 } } }],
});
