import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e-ycloud", timeout: 30000, workers: 1, retries: 0,
  reporter: "list", outputDir: "../output/ycloud-coexistence-20261109/browser",
  use: { baseURL: "http://127.0.0.1:6027", screenshot: "only-on-failure", trace: "retain-on-failure" },
  webServer: { command: "node node_modules/vite/bin/vite.js --config e2e-ycloud/vite.config.ts", url: "http://127.0.0.1:6027/e2e-ycloud/fixture.html", reuseExistingServer: false },
  projects: [{ name: "desktop", use: { viewport: { width: 1440, height: 1000 } } }, { name: "mobile", use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } }],
});
