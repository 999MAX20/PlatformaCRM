import { defineConfig } from "@playwright/test";
import clinical from "./playwright.template-docx.config";

export default defineConfig({ ...clinical, testMatch: ["medical-signing.spec.ts"],
  webServer: Array.isArray(clinical.webServer) ? clinical.webServer.map((server, index) =>
    index === 0 ? { ...server, env: { ...server.env, E2E_MEDICAL_SIGNING: "1" } } : server) : clinical.webServer,
});
