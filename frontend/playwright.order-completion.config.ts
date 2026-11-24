import {defineConfig} from "@playwright/test";
import clinical from "./playwright.clinical.config";
export default defineConfig({...clinical,testMatch:["order-completion.spec.ts"]});
