import { defineConfig } from "@playwright/test";
import signing from "./playwright.signing.config";

export default defineConfig({ ...signing, testMatch: ["medical-final-correction.spec.ts"] });
