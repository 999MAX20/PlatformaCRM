import assert from "node:assert/strict";
import test from "node:test";
import { connectSpeechStream, pcmBase64 } from "../../src/api/speechStream.ts";

class Socket {
  static current;
  bufferedAmount = 0;
  sent = [];
  closed = false;
  constructor(url) { this.url = url; Socket.current = this; }
  send(value) { this.sent.push(JSON.parse(value)); }
  close() { this.closed = true; }
  event(value) { this.onmessage?.({ data: JSON.stringify(value) }); }
}
async function start(t) {
  const original = globalThis.WebSocket;
  globalThis.WebSocket = Socket;
  t.after(() => { globalThis.WebSocket = original; });
  const partials = [], failures = [], controller = new AbortController();
  const promise = connectSpeechStream({ token: "test-single-use", language: "kk", signal: controller.signal,
    onPartial: text => partials.push(text), onFailure: error => failures.push(error.code) });
  const socket = Socket.current;
  socket.event({ message_type: "session_started" });
  return { stream: await promise, socket, partials, failures, controller };
}
test("PCM preserves samples and clamps endpoints", () => {
  const bytes = Buffer.from(pcmBase64(new Float32Array([-2, 0, 2])), "base64");
  assert.deepEqual([0, 2, 4].map(i => bytes.readInt16LE(i)), [-32768, 0, 32767]);
});
test("partial replacement stays uncommitted until explicit finish; final is authoritative", async t => {
  const { stream, socket, partials } = await start(t);
  const url = new URL(socket.url);
  assert.equal(url.searchParams.get("model_id"), "scribe_v3_live");
  assert.equal(url.searchParams.get("enable_logging"), "false");
  assert.equal(url.searchParams.get("secondary_languages"), "ru");
  stream.send(new Float32Array([.5]));
  socket.event({ message_type: "partial_transcript", text: "Әсел" });
  socket.event({ message_type: "partial_transcript", text: "Әсел Сынақ" });
  assert.deepEqual(partials, ["Әсел", "Әсел Сынақ"]);
  assert.ok(socket.sent.every(x => !x.commit));
  const done = stream.finish();
  assert.equal(socket.sent.at(-1).commit, true);
  socket.event({ message_type: "committed_transcript", text: "Әсем Сынақ" });
  assert.equal(await done, "Әсем Сынақ");
  assert.equal(socket.closed, true);
});
test("privacy warning closes stream and suppresses subsequent audio", async t => {
  const { stream, socket, failures } = await start(t);
  socket.event({ message_type: "warning", warning: "provider detail must not surface" });
  stream.send(new Float32Array(128));
  assert.deepEqual(failures, ["provider_rejected"]);
  assert.equal(socket.sent.length, 0);
  assert.equal(socket.closed, true);
});
test("abort rejects pending commit and no reconnect occurs", async t => {
  const { stream, socket, controller, failures } = await start(t);
  const done = stream.finish(); controller.abort();
  await assert.rejects(done, { code: "provider_unavailable" });
  assert.equal(socket.closed, true);
  assert.deepEqual(failures, []);
});
test("backpressure fails without forwarding audio", async t => {
  const { stream, socket, failures } = await start(t);
  socket.bufferedAmount = 300000;
  stream.send(new Float32Array(128));
  assert.deepEqual(failures, ["provider_unavailable"]);
  assert.equal(socket.sent.length, 0);
});

test("oversized text is rejected without rendering it", async t => {
  const { socket, failures, partials } = await start(t);
  socket.event({ message_type: "partial_transcript", text: "x".repeat(4001) });
  assert.deepEqual(failures, ["invalid_response"]);
  assert.deepEqual(partials, []);
  assert.equal(socket.closed, true);
});

for (const operation of ["send", "finish"]) {
  test(`socket send failure during ${operation} closes and rejects cleanly`, async t => {
    const { stream, socket, failures } = await start(t);
    socket.send = () => { throw new Error("transport closed"); };
    if (operation === "finish") await assert.rejects(stream.finish(), { code: "provider_unavailable" });
    else stream.send(new Float32Array(128));
    assert.deepEqual(failures, ["provider_unavailable"]);
    assert.equal(socket.closed, true);
  });
}
test("unexpected committed segments cannot silently drop earlier words", async t => {
  const { socket, failures } = await start(t);
  socket.event({ message_type: "committed_transcript", text: "unexpected segment" });
  assert.deepEqual(failures, ["invalid_response"]);
});
