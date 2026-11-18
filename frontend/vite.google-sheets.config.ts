import { mergeConfig } from "vite";
import { fileURLToPath } from "node:url";
import base from "./vite.config";

if (process.env.ZANI_QUALITY_GATE !== "1") throw new Error("Use the isolated Google Sheets verification runner.");
export default mergeConfig(base, { resolve: { alias: [{ find: /^.*\/api\/googlePicker$/,
  replacement: fileURLToPath(new URL("./e2e/google-picker-fixture.ts", import.meta.url)) }] } });
