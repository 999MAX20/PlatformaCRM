import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [{
    name: "legacy-widget-filename",
    generateBundle(_options, bundle) {
      const widget = bundle["platformacrm-widget.js"];
      if (widget?.type === "chunk") {
        this.emitFile({ type: "asset", fileName: "zani-widget.js", source: widget.code });
      }
    },
  }],
  build: {
    outDir: "dist/widget",
    emptyOutDir: true,
    minify: true,
    lib: {
      entry: resolve(__dirname, "src/index.ts"),
      name: "PlatformaCRMWidget",
      formats: ["iife"],
    },
    rollupOptions: {
      output: {
        entryFileNames: "platformacrm-widget.js",
      },
    },
  },
});
