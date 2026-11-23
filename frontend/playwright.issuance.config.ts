import { defineConfig } from "@playwright/test";
import signing from "./playwright.signing.config";

export default defineConfig({ ...signing, testMatch: ["medical-issuance.spec.ts"],
  webServer: Array.isArray(signing.webServer) ? signing.webServer.map((server, index) =>
    index === 0 ? { ...server, env: { ...server.env, E2E_MEDICAL_ISSUANCE: "1" } } : server) : signing.webServer,
});
