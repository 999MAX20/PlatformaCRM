import { defineConfig } from "@playwright/test";
import clinical from "./playwright.clinical.config";
export default defineConfig({ ...clinical, testMatch: ["medical-reception-duty.spec.ts"] });
