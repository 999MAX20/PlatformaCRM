import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: process.env.GOOGLE_ENTRY_LIVE === "1" ? "google-entry-live.spec.ts" : "google-entry-layout.spec.ts",
  workers: 1,
  reporter: "list",
  use: {
    baseURL: process.env.GOOGLE_ENTRY_URL || "http://127.0.0.1:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
});
