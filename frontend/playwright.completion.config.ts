import { defineConfig } from "@playwright/test";
import clinical from "./playwright.signing.config";

export default defineConfig({ ...clinical, testMatch: ["medical-completion.spec.ts"] });
