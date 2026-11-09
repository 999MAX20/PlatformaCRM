import assert from "node:assert/strict";
import test from "node:test";
import { eventFrames, runAnnouncementEvents, waitForReconnect } from "../../src/api/announcementEventStream.ts";

const frame = event => `event: ${event}\ndata: {}\n\n`;
const stream = (...chunks) => new Response(new ReadableStream({
  start(controller) {
    chunks.forEach(chunk => controller.enqueue(new TextEncoder().encode(chunk)));
    controller.close();
  },
}), { headers: { "Content-Type": "text/event-stream" } });

test("SSE frames handle fragmentation, comments and multiple events without reading data", () => {
  const events = [];
  const parse = eventFrames(event => events.push(event));
  parse(": heartbeat\n\neve");
  parse("nt: ready\ndata: {}\n");
  parse("\n" + frame("changed"));
  assert.deepEqual(events, ["ready", "changed"]);
  assert.throws(() => parse("x".repeat(65_537)), /Invalid event stream/);
});

test("initial connect and reconnect both resync even when disconnected changes were missed", async () => {
  const controller = new AbortController();
  let connections = 0, invalidations = 0;
  await runAnnouncementEvents({
    signal: controller.signal,
    connect: async () => { connections++; return stream(frame("ready")); },
    reauthenticate: async () => assert.fail("no auth recovery needed"),
    forbidden: async () => assert.fail("not forbidden"),
    invalidate: async () => { if (++invalidations === 2) controller.abort(); },
    wait: async () => {},
  });
  assert.equal(connections, 2);
  assert.equal(invalidations, 2);
});

test("changes resync and forbidden stops retries, removing stale monitoring", async () => {
  const controller = new AbortController();
  let refreshed = 0, denied = 0;
  await runAnnouncementEvents({
    signal: controller.signal,
    connect: async () => stream(frame("ready"), frame("changed"), frame("forbidden")),
    reauthenticate: async () => assert.fail(),
    invalidate: async () => { refreshed++; },
    forbidden: async () => { denied++; },
    wait: async () => assert.fail("must stop"),
  });
  assert.equal(refreshed, 2);
  assert.equal(denied, 1);
});

test("401 refreshes once and uses a new connection; repeated auth failure stops", async () => {
  let opened = 0, refreshed = 0;
  await runAnnouncementEvents({
    signal: new AbortController().signal,
    connect: async () => { opened++; return new Response(null, { status: 401 }); },
    reauthenticate: async () => { refreshed++; },
    invalidate: async () => assert.fail(), forbidden: async () => assert.fail(),
    wait: async () => assert.fail(),
  });
  assert.equal(opened, 2);
  assert.equal(refreshed, 1);
});

test("in-stream expiry refreshes credentials and resyncs after reconnect", async () => {
  const controller = new AbortController();
  let connections = 0, refreshes = 0, invalidations = 0;
  await runAnnouncementEvents({
    signal: controller.signal,
    connect: async () => ++connections === 1 ? stream(frame("ready"), frame("reauthenticate")) : stream(frame("ready")),
    reauthenticate: async () => { refreshes++; },
    invalidate: async () => { if (++invalidations === 2) controller.abort(); },
    forbidden: async () => assert.fail(), wait: async () => {},
  });
  assert.equal(refreshes, 1);
  assert.equal(connections, 2);
});

test("broker failures back off and cancellation stops further connections", async () => {
  const controller = new AbortController();
  const delays = [];
  await runAnnouncementEvents({
    signal: controller.signal,
    connect: async () => new Response(null, { status: 503 }),
    reauthenticate: async () => assert.fail(), invalidate: async () => assert.fail(), forbidden: async () => assert.fail(),
    wait: async delay => { delays.push(delay); if (delays.length === 9) controller.abort(); },
  });
  assert.deepEqual(delays, [500, 1000, 2000, 4000, 8000, 16000, 30000, 30000, 30000]);
});

test("silent stalled stream is cancelled and reconnects without a sixty-second wait", async () => {
  const controller = new AbortController();
  let cancelled = 0, connected = 0;
  await runAnnouncementEvents({
    signal: controller.signal, idleTimeout: 10,
    connect: async () => {
      connected++;
      return new Response(new ReadableStream({ cancel() { cancelled++; } }),
        { headers: { "Content-Type": "text/event-stream" } });
    },
    reauthenticate: async () => assert.fail(), invalidate: async () => assert.fail(), forbidden: async () => assert.fail(),
    wait: async () => { controller.abort(); },
  });
  assert.equal(cancelled, 1);
  assert.equal(connected, 1);
});

test("abort interrupts reconnect delay", async () => {
  const controller = new AbortController();
  const waiting = waitForReconnect(30_000, controller.signal);
  controller.abort();
  await waiting;
});
