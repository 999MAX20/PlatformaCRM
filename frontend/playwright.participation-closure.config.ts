import { defineConfig } from "@playwright/test";
import clinical from "./playwright.completion.config";
export default defineConfig({ ...clinical, testMatch: ["medical-participation-closure.spec.ts"] });
