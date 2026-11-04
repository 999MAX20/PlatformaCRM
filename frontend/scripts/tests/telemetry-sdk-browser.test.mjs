import assert from "node:assert/strict";
import test from "node:test";
import { build } from "esbuild";
import { chromium } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { gunzipSync } from "node:zlib";

test("installed SDK browser pipelines sanitize automatic and manual URL metadata", async () => {
  const bundled = await build({ stdin: {
    contents: `import * as monitoring from './src/lib/monitoring';
      import * as sentry from '@sentry/react'; import posthog from 'posthog-js';
      window.probe = { monitoring, sentry, posthog }; monitoring.initFrontendMonitoring();`,
    resolveDir: fileURLToPath(new URL("../..", import.meta.url)), loader: "ts",
  }, bundle: true, write: false, format: "iife", platform: "browser", define: {
    "import.meta.env": JSON.stringify({ MODE: "test", VITE_SENTRY_DSN: "https://synthetic@telemetry.invalid/1", VITE_POSTHOG_KEY: "synthetic", VITE_POSTHOG_HOST: "https://analytics.invalid" }),
  } });
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({ userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36" });
    const sentryPayloads = [], posthogPayloads = [], flagRequests = [];
    await context.route("**/*", async route => {
      const request = route.request();
      if (request.url().includes("analytics.invalid/flags/")) flagRequests.push(request.url());
      if (request.url().startsWith("https://crm.invalid/") && request.isNavigationRequest()) {
        await route.fulfill({ contentType: "text/html", body: "<!doctype html><title>Telemetry fixture</title><button>Save</button>" });
      } else {
        if (request.url().startsWith("https://telemetry.invalid/") && request.postData()) sentryPayloads.push(request.postData());
        if (request.url().startsWith("https://analytics.invalid/") && request.postDataBuffer()) posthogPayloads.push(request.postDataBuffer());
        await route.fulfill({ status: 200, contentType: "application/json", body: "{}", headers: { "access-control-allow-origin": "*" } });
      }
    });
    const page = await context.newPage();
    page.on("console", message => { if (message.type() === "error") console.error("fixture browser:", message.text()); });
    page.on("pageerror", error => console.error("fixture error:", error.message));
    await page.goto("https://crm.invalid/invite/SYNTHETIC_REFERRER");
    await page.goto("https://crm.invalid/reset-password/SYNTHETIC_UID/SYNTHETIC_TOKEN", { referer: "https://crm.invalid/invite/SYNTHETIC_REFERRER" });
    await page.addScriptTag({ content: bundled.outputFiles[0].text });
    await page.waitForFunction(() => window.probe.sentry.getClient() && window.probe.posthog.__loaded);
    const observed = await page.evaluate(async () => {
      const { monitoring, posthog, sentry } = window.probe;
      const events = [];
      const beforeSend = posthog.config.before_send;
      posthog.set_config({ opt_out_useragent_filter: true, request_batching: false, disable_compression: true, before_send: event => {
        const clean = beforeSend(event); events.push(clean); return clean;
      } });
      sentry.addBreadcrumb({ category: "navigation", data: { from: document.referrer, to: location.href } });
      monitoring.captureFrontendError(new Error(`synthetic failure ${location.href}`), { nested: { url: location.href }, count: 3 });
      sentry.captureEvent({ type: "transaction", transaction: location.href,
        start_timestamp: Date.now() / 1000 - 1, timestamp: Date.now() / 1000,
        contexts: { trace: { trace_id: "a".repeat(32), span_id: "b".repeat(16), op: "test", data: { "url.full": location.href } } },
        spans: [{ trace_id: "a".repeat(32), span_id: "c".repeat(16), parent_span_id: "b".repeat(16), op: "http.client",
          description: location.href, data: { "http.request.header.referer": document.referrer },
          start_timestamp: Date.now() / 1000 - 1, timestamp: Date.now() / 1000 }],
      });
      monitoring.trackFrontendEvent("saved", { nested: { url: location.href }, count: 3 });
      posthog.capture("$pageview");
      posthog.capture("$autocapture", { $elements: [{ href: document.referrer }] });
      posthog.reloadFeatureFlags();
      history.pushState({}, "", "/clients/42");
      monitoring.trackFrontendEvent("ordinary", { count: 4 });
      await sentry.flush(3000);
      return { events, replayDisabled: posthog.config.disable_session_recording, referrer: document.referrer };
    });
    await page.waitForTimeout(250);
    assert.match(observed.referrer, /SYNTHETIC_REFERRER/);
    assert.equal(observed.replayDisabled, true);
    assert.equal(observed.events.length, 4, JSON.stringify(observed));
    assert.doesNotMatch(JSON.stringify(observed.events), /SYNTHETIC_(?:UID|TOKEN|REFERRER)/);
    assert.equal(observed.events[0].properties.count, 3);
    assert.equal(observed.events[0].properties.$current_url, "https://crm.invalid/reset-password/:uid/:token");
    assert.equal(observed.events[3].properties.$current_url, "https://crm.invalid/clients/42");
    assert.ok(sentryPayloads.length > 0, "Sentry transport must emit");
    assert.doesNotMatch(sentryPayloads.join("\n"), /SYNTHETIC_(?:UID|TOKEN|REFERRER)/);
    assert.match(sentryPayloads.join("\n"), /synthetic failure/);
    assert.match(sentryPayloads.join("\n"), /reset-password\/:uid\/:token/);
    assert.match(sentryPayloads.join("\n"), /"type":"transaction"/);
    assert.ok(posthogPayloads.length > 0, "PostHog transport must emit");
    for (const raw of posthogPayloads) {
      let payload = (raw[0] === 0x1f && raw[1] === 0x8b ? gunzipSync(raw) : raw).toString("utf8");
      const encoded = new URLSearchParams(payload).get("data");
      if (encoded) payload = Buffer.from(encoded, "base64").toString("utf8");
      assert.ok(JSON.parse(payload), "Actual PostHog payload must be decoded before inspection");
      assert.doesNotMatch(payload, /SYNTHETIC_(?:UID|TOKEN|REFERRER)/);
    }
    // The previous document has persisted initial URL/referrer properties in this profile.
    await page.reload();
    await page.addScriptTag({ content: bundled.outputFiles[0].text });
    await page.waitForFunction(() => window.probe.posthog.__loaded);
    await page.evaluate(() => window.probe.posthog.reloadFeatureFlags());
    await page.waitForTimeout(250);
    assert.equal(flagRequests.length, 0);
    await context.close();
  } finally {
    await browser.close();
  }
});
