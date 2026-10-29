import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";
import { enqueueLeadCommand, replayLeadCommands, retryBlockedReason, withLeadQueue } from "../../src/lib/leadOfflineCommands.ts";
import { leadOfflineScope, readLeadOfflineData, clearLeadOfflineStorage } from "../../src/lib/leadOfflineStorage.ts";

const scope = leadOfflineScope({ id: 1, role: "business_owner" }, 20);
const active = () => true;
const note = id => ({ id: String(id), type: "note", leadId: 100, text: `Note ${id}`, createdAt: new Date().toISOString() });
beforeEach(() => {
  const values = new Map();
  globalThis.localStorage = { get length() { return values.size; }, key: i => [...values.keys()][i],
    getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) };
  globalThis.window = new EventTarget();
  let tail = Promise.resolve();
  Object.defineProperty(globalThis, "navigator", { configurable: true, value: { onLine: true,
    locks: { request: (_key, fn) => { const result = tail.then(fn); tail = result.catch(() => {}); return result; } } } });
});
test("41 commands survive acceptance/reload and concurrent writers without eviction", async () => {
  await Promise.all(Array.from({ length: 41 }, (_, i) => enqueueLeadCommand(scope, active, note(i))));
  assert.equal(readLeadOfflineData(scope).queue.length, 41);
  assert.deepEqual(readLeadOfflineData(scope).queue.map(x => x.id), Array.from({ length: 41 }, (_, i) => String(i)));
});
test("quota failure rejects new input and leaves accepted commands intact", async () => {
  await enqueueLeadCommand(scope, active, note(1));
  localStorage.setItem = () => { throw new Error("quota"); };
  await assert.rejects(enqueueLeadCommand(scope, active, note(2)), /queueStorageError/);
  assert.deepEqual(readLeadOfflineData(scope).queue.map(x => x.id), ["1"]);
});
test("failure to persist command identity prevents any network call", async () => {
  await enqueueLeadCommand(scope, active, note(1));
  localStorage.setItem = () => { throw new Error("quota"); };
  let sent = 0;
  await assert.rejects(replayLeadCommands(scope, active, async () => sent++, () => "network"));
  assert.equal(sent, 0);
});
test("lost committed response keeps identity/payload for manual retry after reload", async () => {
  await enqueueLeadCommand(scope, active, note(1));
  const effects = new Map(); let requests = 0;
  const send = async item => {
    assert.equal(readLeadOfflineData(scope).queue[0].commandKey, item.commandKey);
    effects.set(item.commandKey, item.text); requests++;
    if (requests === 1) throw new Error("lost response");
  };
  await replayLeadCommands(scope, active, send, () => "network");
  const first = readLeadOfflineData(scope).queue[0];
  assert.equal(first.errorKey, "network");
  await replayLeadCommands(scope, active, send, () => "network");
  assert.equal(requests, 1, "no implicit retry loop");
  await withLeadQueue(scope, active, (data, save) => { delete data.queue[0].errorKey; save(); });
  await replayLeadCommands(scope, active, send, () => "network");
  assert.equal(effects.size, 1); assert.equal(requests, 2);
  assert.equal(readLeadOfflineData(scope).queue.length, 0);
});
test("one conflict stays visible without starving an unrelated command", async () => {
  await enqueueLeadCommand(scope, active, note(1)); await enqueueLeadCommand(scope, active, note(2));
  const count = await replayLeadCommands(scope, active, async item => { if (item.id === "1") throw new Error("409"); }, () => "conflict");
  assert.equal(count, 1); assert.equal(readLeadOfflineData(scope).queue[0].errorKey, "conflict");
});
test("two tabs replay the same stored command only once", async () => {
  await enqueueLeadCommand(scope, active, note(1)); let calls = 0;
  await Promise.all([1, 2].map(() => replayLeadCommands(scope, active, async () => calls++, () => "network")));
  assert.equal(calls, 1);
});
test("logout during request cannot recreate private data or send subsequent work", async () => {
  await enqueueLeadCommand(scope, active, note(1)); await enqueueLeadCommand(scope, active, note(2));
  let current = true; let sent = 0;
  await replayLeadCommands(scope, () => current, async () => { sent++; current = false; clearLeadOfflineStorage(); }, () => "network");
  assert.equal(sent, 1); assert.equal(localStorage.length, 0);
});
test("legacy unknown-result work and expired keyed work are retained without replay", async () => {
  await withLeadQueue(scope, active, (data, save) => {
    data.queue.push(note(1), { ...note(2), version: 2, commandKey: `lead-offline:${Date.now()-3600001}:12345678-1234-1234-1234-123456789abc` }); save();
  });
  let sent = 0; await replayLeadCommands(scope, active, async () => sent++, () => "network");
  assert.equal(sent, 0);
  assert.deepEqual(readLeadOfflineData(scope).queue.map(x => x.errorKey), ["leads.queueLegacy", "leads.queueExpired"]);
  assert.equal(retryBlockedReason({ ...note(3), version: 2 }), undefined);
});
test("unsupported locking fails explicitly instead of permitting a lost-write race", async () => {
  navigator.locks = undefined;
  await assert.rejects(enqueueLeadCommand(scope, active, note(1)), /queueStorageError/);
});
