import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import vm from "node:vm";
import ts from "typescript";

function load(name, globals = {}, dependencies = {}) {
  const exports = {};
  const source = fs.readFileSync(new URL(`../../src/lib/${name}.ts`, import.meta.url), "utf8")
    .replaceAll("import.meta.env", "environment");
  vm.runInNewContext(ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS,
  } }).outputText, { exports, Date, URL, console, require: name => {
    assert.ok(name in dependencies, `Unexpected dependency ${name}`);
    return dependencies[name];
  }, ...globals });
  return exports;
}
const privacy = load("telemetryPrivacy");
const { redactTelemetryUrls: redact, sanitizeTelemetry: sanitize } = privacy;
const reset = "https://crm.invalid/reset-password/SYNTHETIC_UID/SYNTHETIC_TOKEN?token=SYNTHETIC_TOKEN";
const invite = "https://crm.invalid/invite/SYNTHETIC_TOKEN";

for (const [label, value] of Object.entries({
  reset, invite, preview: "/api/team/invitations/preview/SYNTHETIC_TOKEN/",
  encoded: encodeURIComponent(reset), nested: encodeURIComponent(encodeURIComponent(invite)),
  query: `https://crm.invalid/error?next=${encodeURIComponent(reset)}`,
  fragment: `https://crm.invalid/#${encodeURIComponent(invite)}`,
  escaped: "https:\\/\\/crm.invalid\\/invite\\/SYNTHETIC_TOKEN",
  case: "/INVITE/SYNTHETIC_TOKEN", whitespace: "/invite/first%20SYNTHETIC_TOKEN",
  malformed: "/invite/%zzSYNTHETIC_TOKEN", encodedRoute: "/%69nvite/SYNTHETIC_TOKEN",
})) test(`bearer removed: ${label}`, () => {
  const result = redact(value);
  assert.doesNotMatch(result, /SYNTHETIC_(?:TOKEN|UID)/);
  assert.match(result, /:token/);
  assert.equal(redact(result), result);
});

test("ordinary routes, context, query strings and text remain identical", () => {
  for (const value of ["/clients/42?q=hello%20world", "https://crm.invalid/calendar#day", "Client saved", "/invites/42", "/invite-settings", ""]) assert.equal(redact(value), value);
});

test("nested arrays, keys, repeated references and cycles without mutation", () => {
  const shared = { url: reset, count: 3 }, date = new Date("2026-11-04T00:00:00Z");
  const source = { a: shared, b: shared, array: [null, false, date, invite], [invite]: "value" };
  source.self = source;
  const result = sanitize(source);
  assert.equal(result.a.url, "https://crm.invalid/reset-password/:uid/:token");
  assert.equal(result.b.count, 3);
  assert.equal(result.b.url, result.a.url);
  assert.equal(result.array[2], date);
  assert.equal(result.self, "[Circular]");
  assert.doesNotMatch(JSON.stringify(result), /SYNTHETIC/);
  assert.equal(source.a.url, reset);
  assert.equal(source.self, source);
});

test("deep and multiply encoded values fail closed", () => {
  let encoded = invite;
  for (let i = 0; i < 12; i++) encoded = encodeURIComponent(encoded);
  assert.equal(redact(encoded), "[Encoded telemetry value omitted]");
  let nested = { url: invite };
  for (let i = 0; i < 40; i++) nested = { child: nested };
  assert.doesNotMatch(JSON.stringify(sanitize(nested)), /SYNTHETIC/);
});

function browser(referrer = "", href = reset, existing = false) {
  const scripts = [], listeners = {};
  const window = { location: new URL(href), addEventListener: (name, fn) => { listeners[name] = fn; } };
  window.history = { pushState(_state, _unused, url) { window.location = new URL(url, window.location); } };
  const document = { referrer, querySelector: () => existing ? {} : null,
    createElement: () => ({ dataset: {} }), head: { appendChild: script => scripts.push(script) } };
  const api = load("plausibleMonitoring", { window, document }, { "./telemetryPrivacy": privacy });
  return { api, window, scripts, listeners };
}

test("Plausible manually queues sanitized initial, SPA and restored pageviews", () => {
  const b = browser();
  b.api.initPlausibleMonitoring("crm.invalid");
  b.api.initPlausibleMonitoring("crm.invalid");
  assert.equal(b.scripts.length, 1);
  assert.match(b.scripts[0].src, /script.manual.js$/);
  assert.equal(b.scripts[0].referrerPolicy, "no-referrer");
  b.window.history.pushState({}, "", "/clients/42");
  b.window.history.pushState({}, "", "/clients/42?q=1");
  b.window.location = new URL(invite);
  b.listeners.popstate();
  b.listeners.pageshow({ persisted: true });
  b.api.trackPlausibleEvent("saved", { nested: { url: reset }, count: 2 });
  const queue = b.window.plausible.q;
  assert.equal(queue.length, 5);
  assert.equal(queue[1][1].url, "https://crm.invalid/clients/42");
  assert.equal(queue[4][1].props.count, 2);
  assert.doesNotMatch(JSON.stringify(queue), /SYNTHETIC/);
  for (let i = 0; i < 110; i++) b.api.trackPlausibleEvent("saved");
  assert.equal(queue.length, 100);
});

test("Plausible disabled, sensitive referrer and foreign tracker do not emit", () => {
  for (const [referrer, domain, existing] of [[reset, "crm.invalid", false], ["", undefined, false], ["", "crm.invalid", true]]) {
    const b = browser(referrer, reset, existing);
    b.api.initPlausibleMonitoring(domain);
    b.api.trackPlausibleEvent("saved");
    assert.equal(b.scripts.length, 0);
    assert.equal(b.window.plausible, undefined);
  }
});

function monitoring(environment) {
  const calls = { sentry: [], posthog: [], plausible: [] };
  const sentry = { init: options => { calls.sentryOptions = options; }, captureException: (...args) => calls.sentry.push(args) };
  const posthog = { default: { init: (_key, options) => { calls.posthogOptions = options; }, capture: (...args) => calls.posthog.push(args) } };
  const api = load("monitoring", { environment }, { "./telemetryPrivacy": privacy,
    "./plausibleMonitoring": { initPlausibleMonitoring: domain => calls.plausible.push(domain), trackPlausibleEvent() {} },
    "@sentry/react": sentry, "posthog-js": posthog });
  return { api, calls };
}

test("disabled SDKs do not initialize or capture", async () => {
  const { api, calls } = monitoring({});
  api.initFrontendMonitoring();
  api.trackFrontendEvent("saved");
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(calls.sentryOptions, undefined);
  assert.equal(calls.posthogOptions, undefined);
  assert.equal(calls.posthog.length, 0);
});

test("delayed imports preserve events and configure final enriched hooks", async () => {
  const { api, calls } = monitoring({ VITE_SENTRY_DSN: "synthetic", VITE_POSTHOG_KEY: "synthetic", MODE: "test" });
  api.initFrontendMonitoring();
  api.initFrontendMonitoring();
  api.captureFrontendError(new Error("synthetic"), { url: reset });
  api.trackFrontendEvent("saved", { url: invite, count: 2 });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(calls.sentry.length, 1);
  assert.equal(calls.posthog.length, 1);
  assert.doesNotMatch(JSON.stringify(calls.posthog), /SYNTHETIC/);
  for (const hook of ["beforeSend", "beforeSendTransaction", "beforeSendSpan", "beforeBreadcrumb"]) {
    const input = { request: { url: reset, headers: { Referer: invite } }, contexts: { trace: { data: { "url.full": reset } } }, ordinary: 12 };
    assert.doesNotMatch(JSON.stringify(calls.sentryOptions[hook](input)), /SYNTHETIC/);
    assert.equal(calls.sentryOptions[hook](input).ordinary, 12);
  }
  assert.equal(calls.posthogOptions.disable_session_recording, true);
  assert.equal(calls.posthogOptions.advanced_disable_flags, true);
  assert.equal(calls.posthogOptions.advanced_disable_feature_flags, true);
  const enriched = { event: "$autocapture", properties: { $current_url: reset, $referrer: invite, $initial_referrer: invite, $elements: [{ href: invite }] } };
  assert.doesNotMatch(JSON.stringify(calls.posthogOptions.before_send(enriched)), /SYNTHETIC/);
});
