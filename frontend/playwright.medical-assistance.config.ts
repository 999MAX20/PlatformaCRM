import {defineConfig} from "@playwright/test";
import clinical from "./playwright.clinical.config";
export default defineConfig({...clinical,testMatch:["medical-assistance.spec.ts","order-assistance.spec.ts"],use:{...clinical.use,
 permissions:["microphone"],launchOptions:{args:["--use-fake-device-for-media-stream","--use-fake-ui-for-media-stream"]}}});
