import { defineConfig } from "@playwright/test";
import clinical from "./playwright.clinical.config";

export default defineConfig({ ...clinical, testMatch: ["medical-document-rules.spec.ts", "medical-document-rules-locales.spec.ts"] });
