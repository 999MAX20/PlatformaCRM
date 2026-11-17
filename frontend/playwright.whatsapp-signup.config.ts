import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e", testMatch: "whatsapp-signup.spec.ts", workers: 1,
  timeout: 30000, reporter: "list",
  outputDir: "../output/playwright/whatsapp-signup-20261114",
  use: { baseURL: process.env.E2E_BASE_URL || "http://127.0.0.1:5173", browserName: "chromium", screenshot: "only-on-failure" },
});
