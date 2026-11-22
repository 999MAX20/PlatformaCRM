import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e", testMatch: ["medical-patient.spec.ts", "medical-patient-search.spec.ts", "medical-identity-correction.spec.ts", "medical-registration.spec.ts"], workers: 1, retries: 0,
  timeout: 60_000, expect: { timeout: 12_000 }, reporter: "list",
  outputDir: process.env.E2E_MEDICAL_OUTPUT_DIR || "../output/playwright/medical",
  use: { baseURL: process.env.E2E_BASE_URL, screenshot: "only-on-failure", trace: "retain-on-failure" },
  webServer: [
    { command: `"${process.env.E2E_PYTHON}" e2e/medical-runtime.py`, url: `${process.env.E2E_API_BASE_URL}/health/`, reuseExistingServer: false, timeout: 180_000 },
    { command: `npm run dev -- --host 127.0.0.1 --port ${process.env.E2E_FRONTEND_PORT} --strictPort`, url: process.env.E2E_BASE_URL!, reuseExistingServer: false, timeout: 120_000 },
  ],
});
