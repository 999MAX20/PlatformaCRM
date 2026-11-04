import base from "./playwright.config";
import { defineConfig } from "@playwright/test";
const servers = base.webServer as { command: string }[];
export default defineConfig({ ...base, webServer: [
  { ...servers[0], command: `"${process.env.E2E_PYTHON}" ../output/remediation-c05-20261104/serve.py` },
  servers[1],
] });
