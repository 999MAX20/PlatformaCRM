import { defineConfig } from "@playwright/test";
import base from "./playwright.channel-setup.config";

export default defineConfig(base, {
  testMatch: ["channel-setup.spec.ts", "whatsapp-signup.spec.ts"],
  reporter: [["list"], ["json", { outputFile: "../output/channels-reference-20261114/results.json" }]],
  outputDir: "../output/channels-reference-20261114/browser",
});
