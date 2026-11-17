import { isAbsolute, relative, resolve, sep } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [{
    name: "legacy-widget-filename",
    configResolved(config) {
      const projectRoot = resolve(__dirname, "../..");
      const outputPath = resolve(config.root, config.build.outDir);
      const projectRelativePath = relative(projectRoot, outputPath);
      if (!projectRelativePath || projectRelativePath === ".." || projectRelativePath.startsWith(`..${sep}`) || isAbsolute(projectRelativePath)) {
        throw new Error("Widget build output must stay inside PlatformaCRM. From frontend, use --outDir ../output/<task>/widget.");
      }
    },
    generateBundle(_options, bundle) {
      const widget = bundle["platformacrm-widget.js"];
      if (widget?.type === "chunk") {
        this.emitFile({ type: "asset", fileName: "zani-widget.js", source: widget.code });
      }
    },
  }],
  build: {
    outDir: resolve(__dirname, "../dist/widget"),
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
