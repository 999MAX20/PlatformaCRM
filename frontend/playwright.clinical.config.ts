import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e", testMatch: ["medical-plan-booking.spec.ts", "medical-plan-links.spec.ts", "medical-orders.spec.ts", "medical-rollout.spec.ts", "medical-template-availability.spec.ts", "medical-credentials.spec.ts", "medical-documents.spec.ts", "medical-clinical.spec.ts", "medical-clinical-recovery.spec.ts", "medical-history-recovery.spec.ts", "medical-tooth.spec.ts", "medical-participation.spec.ts", "medical-proposal.spec.ts", "medical-notifications.spec.ts", "medical-roles.spec.ts", "medical-templates.spec.ts"], workers: 1, retries: 0,
  timeout: 60_000, expect: { timeout: 12_000 }, reporter: "list",
  outputDir: process.env.E2E_MEDICAL_OUTPUT_DIR || "../output/playwright/clinical",
  use: { baseURL: process.env.E2E_BASE_URL, screenshot: "only-on-failure", trace: "retain-on-failure" },
  webServer: [
    { command: `"${process.env.E2E_PYTHON}" e2e/clinical-runtime.py`, url: `${process.env.E2E_API_BASE_URL}/health/`, reuseExistingServer: false, timeout: 180_000 },
    { command: `npm run dev -- --host 127.0.0.1 --port ${process.env.E2E_FRONTEND_PORT} --strictPort`, url: process.env.E2E_BASE_URL!, reuseExistingServer: false, timeout: 120_000 },
  ],
});
