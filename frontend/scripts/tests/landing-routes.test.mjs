import assert from "node:assert/strict";
import { createServer as createSocketServer } from "node:net";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { createServer } from "vite";

const root = fileURLToPath(new URL("../../", import.meta.url));

test("landing owns only the exact home URL; auth, workspace and documents keep the SPA", async () => {
  const socket = createSocketServer();
  await new Promise(resolve => socket.listen(0, "127.0.0.1", resolve));
  const port = socket.address().port;
  await new Promise(resolve => socket.close(resolve));
  const server = await createServer({
    root, envFile: false, logLevel: "silent",
    mode: "landing-route-test",
    server: { host: "127.0.0.1", port },
    optimizeDeps: { noDiscovery: true, entries: [] },
  });
  try {
    await server.listen();
    const base = `http://127.0.0.1:${server.httpServer.address().port}`;
    for (const path of ["/", "/?lang=kk", "/index.html?lang=en"]) {
      const response = await fetch(base + path);
      assert.equal(response.status, 200, path);
      const html = await response.text();
      assert.match(html, /\/landing\/app\.js/, path);
      assert.match(html, /href="\/login"/, path);
      assert.doesNotMatch(html, /src="\/src\/main\.tsx"/, path);
    }
    for (const path of ["/login", "/app/calendar", "/platform", "/mfa", "/forgot-password", "/documents", "/invite/fixture"]) {
      const response = await fetch(base + path);
      assert.equal(response.status, 200, path);
      const html = await response.text();
      assert.match(html, /src="\/src\/main\.tsx"/, path);
      assert.doesNotMatch(html, /\/landing\/app\.js/, path);
    }
    for (const path of ["/landing/features.html", "/landing/privacy.html", "/landing/styles.css", "/landing/assets/reception.webp", "/landing/legal-files/ru/terms.docx"]) {
      assert.equal((await fetch(base + path)).status, 200, path);
    }
    const config = await (await fetch(base + "/landing/config.js")).text();
    assert.match(config, /loginUrl: "\/login"/);
    assert.match(config, /digitalUrl: "https:\/\/platformadigital\.kz\/"/);
  } finally {
    await server.close();
  }
});
