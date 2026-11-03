import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync, readdirSync } from "node:fs";
import { createServer as createSocketServer } from "node:net";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { createServer, optimizeDeps, resolveConfig } from "vite";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const options = (port) => ({
  root, envFile: false, mode: "cache-isolation-test", logLevel: "silent",
  server: { host: "127.0.0.1", port, strictPort: false },
  optimizeDeps: { entries: [], noDiscovery: true, include: ["react", "react-dom/client"] },
});
async function reservePort() {
  const server = createSocketServer();
  await new Promise((done, reject) => { server.once("error", reject); server.listen(0, "127.0.0.1", done); });
  return { server, port: server.address().port };
}
function snapshot(directory) {
  return Object.fromEntries(readdirSync(directory).sort().map(name => [name,
    createHash("sha256").update(readFileSync(join(directory, name))).digest("hex")]));
}

test("default config resolves TypeScript without generated JS; ports and build have separate caches", async () => {
  const a = await resolveConfig(options(15431), "serve");
  const b = await resolveConfig(options(15432), "serve");
  const build = await resolveConfig(options(15431), "build");
  assert.equal(a.configFile.replaceAll("\\", "/"), root.replaceAll("\\", "/") + "/vite.config.ts");
  assert.notEqual(a.cacheDir, b.cacheDir);
  assert.notEqual(a.cacheDir, build.cacheDir);
  assert.equal(a.server.strictPort, true);
  assert.equal((await resolveConfig(options(15431), "serve")).cacheDir, a.cacheDir);
  const randomA = await resolveConfig(options(0), "serve");
  const randomB = await resolveConfig(options(0), "serve");
  assert.notEqual(randomA.cacheDir, randomB.cacheDir);
});

test("forced React optimization for another port cannot replace the first server dependency files", async () => {
  const first = await reservePort(), second = await reservePort();
  try {
    const a = await resolveConfig(options(first.port), "serve");
    const b = await resolveConfig(options(second.port), "serve");
    await optimizeDeps(a, true, true);
    const directory = join(a.cacheDir, "deps");
    const before = snapshot(directory);
    assert.ok(before["react.js"]);
    assert.ok(before["react-dom_client.js"]);
    await optimizeDeps(b, true, true);
    assert.deepEqual(snapshot(directory), before);
    await optimizeDeps({ ...b, define: { __CACHE_PROBE__: "true" } }, true, true);
    assert.deepEqual(snapshot(directory), before);
  } finally {
    first.server.close(); second.server.close();
  }
});

test("occupied port fails instead of silently sharing a cache under a different listening port", async () => {
  const occupied = await reservePort();
  let vite;
  try {
    vite = await createServer(options(occupied.port));
    await assert.rejects(vite.listen(), /already in use/);
  } finally {
    await vite?.close(); occupied.server.close();
  }
});
