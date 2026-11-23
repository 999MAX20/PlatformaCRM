import { defineConfig } from "@playwright/test";
import clinical from "./playwright.clinical.config";

export default defineConfig({ ...clinical, testMatch: ["medical-template-docx.spec.ts", "medical-document-docx.spec.ts"],
  webServer: Array.isArray(clinical.webServer) ? clinical.webServer.map((server, index) =>
    index === 0 ? { ...server, env: { ...server.env, E2E_TEMPLATE_DOCX_SCAN: "1", E2E_MEDICAL_TEMPLATES: "1" } } : server) : clinical.webServer,
});
