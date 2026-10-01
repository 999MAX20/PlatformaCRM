import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const router = fs.readFileSync(path.join(frontend, "src/app/router.tsx"), "utf8");
const merchantStart = router.indexOf("const merchantChildren =");
const legacyStart = router.indexOf("const legacyMerchantRoutes =");
const rootStart = router.indexOf("const router = createBrowserRouter");
const platformStart = router.indexOf('path: "/platform"', rootStart);
const appStart = router.indexOf('path: "/app"', platformStart);

export const routes = [...router.matchAll(/path:\s*"([^"]+)"/g)].map((match) => {
  const offset = match.index;
  const group = match[1] === "/app" ? "merchant-layout"
    : match[1] === "/dashboard/*" ? "legacy-redirect"
      : offset >= merchantStart && offset < legacyStart ? "merchant"
    : offset >= legacyStart && offset < rootStart ? "legacy"
      : offset >= platformStart && offset < appStart ? "platform" : "public";
  const route = match[1].startsWith("/") || match[1] === "*" ? match[1]
    : `${group === "platform" ? "/platform" : "/app"}/${match[1]}`;
  const next = router.indexOf("path:", offset + match[0].length);
  const block = router.slice(offset, next < 0 ? undefined : next);
  return {
    route,
    group,
    line: router.slice(0, offset).split("\n").length,
    component: block.match(/<([A-Z]\w*Page)\b/)?.[1] ?? null,
    resource: block.match(/resource:\s*"([^"]+)"/)?.[1] ?? null,
    redirect: block.match(/<Navigate to="([^"]+)"/)?.[1] ?? (block.includes("BusinessRouteRedirect") ? "business route alias" : null),
  };
});

function inventory() {
  const files = [];
  const stack = [path.join(frontend, "src"), path.join(frontend, "widget/src"), path.join(frontend, "public")];
  while (stack.length) {
    const folder = stack.pop();
    for (const entry of fs.readdirSync(folder, { withFileTypes: true })) {
      const absolute = path.join(folder, entry.name);
      if (entry.isDirectory()) { stack.push(absolute); continue; }
      if (!/\.(tsx?|css|svg)$/.test(entry.name)) continue;
      const source = fs.readFileSync(absolute, "utf8");
      const hits = source.split(/\r?\n/).flatMap((line, index) => {
        const literals = [...line.matchAll(/#[\da-f]{3,8}\b|(?:rgb|hsl)a?\((?!var)[^)]*\)/gi)].map((match) => match[0]);
        const utilities = [...line.matchAll(/\b(?:bg|text|border|ring|fill|stroke|from|via|to|accent)-(?:slate|gray|zinc|stone|neutral|orange|amber|yellow|green|emerald|red|rose|blue|sky|cyan|teal|purple|violet|indigo|pink|fuchsia)-\d+\b/g)].map((match) => match[0]);
        const colorAttribute = /\b(?:fill|stroke)=["'{]/.test(line);
        return literals.length || utilities.length || colorAttribute
          ? [{ line: index + 1, literals, utilities, colorAttribute, source: line.trim() }] : [];
      });
      files.push({ file: path.relative(frontend, absolute).replaceAll("\\", "/"), sha256: crypto.createHash("sha256").update(source).digest("hex"), hits });
    }
  }
  return { routes, files: files.sort((left, right) => left.file.localeCompare(right.file)) };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const result = inventory();
  const output = process.argv[2];
  if (!output) throw new Error("Provide an explicit JSON output path");
  fs.writeFileSync(output, `${JSON.stringify(result, null, 2)}\n`);
  console.log(`${result.routes.length} explicit routes; ${result.files.length} source files; ${result.files.filter((file) => file.hits.length).length} files with literals/legacy colors/SVG attributes. Findings require semantic review, not automatic replacement.`);
}
