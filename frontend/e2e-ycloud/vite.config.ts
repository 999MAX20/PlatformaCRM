import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({ plugins: [react()], envDir: false, envPrefix: "YCLOUD_FIXTURE_PUBLIC_", server: { host: "127.0.0.1", port: 6027, strictPort: true } });
