import { defineConfig } from "@playwright/test";
import clinical from "./playwright.template-docx.config";

export default defineConfig({ ...clinical, testMatch: ["medical-document-docx.spec.ts"] });
