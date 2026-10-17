import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";
import { clearLeadOfflineStorage, leadOfflineScope, readLeadOfflineData, writeLeadOfflineData } from "../../src/lib/leadOfflineStorage.ts";

beforeEach(() => {
  const data = new Map();
  globalThis.localStorage = {
    get length() { return data.size; },
    key: index => [...data.keys()][index] ?? null,
    getItem: key => data.get(key) ?? null,
    setItem: (key, value) => data.set(key, value),
    removeItem: key => data.delete(key),
  };
});
const user = { id: 1, role: "business_owner", is_merchant_user: true, businesses: [] };
const lead = { id: 10, business: 20, message: "Private A" };
const note = { id: "pending", type: "note", leadId: 10, text: "Private note", createdAt: "2026-10-17" };
const empty = { leads: [], queue: [] };

test("same user and business retain offline rows and queued work across reload", () => {
  writeLeadOfflineData(leadOfflineScope(user, 20), { leads: [lead], queue: [note] });
  assert.deepEqual(readLeadOfflineData(leadOfflineScope({ ...user }, 20)), { leads: [lead], queue: [note] });
});
test("another account or Business cannot read rows or queued actions", () => {
  writeLeadOfflineData(leadOfflineScope(user, 20), { leads: [lead], queue: [note] });
  assert.deepEqual(readLeadOfflineData(leadOfflineScope({ ...user, id: 2 }, 20)), empty);
  assert.deepEqual(readLeadOfflineData(leadOfflineScope(user, 21)), empty);
  assert.deepEqual(readLeadOfflineData(null), empty);
  assert.deepEqual(readLeadOfflineData(leadOfflineScope(user, 20)), { leads: [lead], queue: [note] });
});
test("a record copied to another account's key is rejected by its identity envelope", () => {
  const first = leadOfflineScope(user, 20);
  const second = leadOfflineScope({ ...user, id: 2 }, 20);
  writeLeadOfflineData(first, { leads: [lead], queue: [note] });
  localStorage.setItem(second.key, localStorage.getItem(first.key));
  assert.deepEqual(readLeadOfflineData(second), empty);
  assert.equal(localStorage.getItem(second.key), null);
});
test("permission narrowing discards the previous authorization snapshot", () => {
  writeLeadOfflineData(leadOfflineScope(user, 20), { leads: [lead], queue: [note] });
  assert.deepEqual(readLeadOfflineData(leadOfflineScope({ ...user, effective_permissions: { "20": [] } }, 20)), empty);
  assert.equal(localStorage.length, 0);
});
test("legacy unscoped private data is discarded rather than adopted by the next login", () => {
  localStorage.setItem("zani_leads_cache", JSON.stringify([lead]));
  localStorage.setItem("zani_leads_offline_queue", JSON.stringify([note]));
  assert.deepEqual(readLeadOfflineData(leadOfflineScope(user, 20)), empty);
  assert.equal(localStorage.length, 0);
});
test("an empty successful snapshot removes earlier rows without dropping pending work", () => {
  const scope = leadOfflineScope(user, 20);
  writeLeadOfflineData(scope, { leads: [lead], queue: [note] });
  writeLeadOfflineData(scope, { leads: [], queue: [note] });
  assert.deepEqual(readLeadOfflineData(scope), { leads: [], queue: [note] });
});
test("mixed-Business rows cannot enter or leave this Business cache", () => {
  const scope = leadOfflineScope(user, 20);
  writeLeadOfflineData(scope, { leads: [lead, { ...lead, business: 21 }], queue: [] });
  assert.deepEqual(readLeadOfflineData(scope).leads, [lead]);
  localStorage.setItem(scope.key, JSON.stringify({ identity: scope.identity, leads: [lead, null, { ...lead, business: 21 }], queue: [] }));
  assert.deepEqual(readLeadOfflineData(scope).leads, [lead]);
});
test("session clear removes all sensitive scopes and legacy records but preserves display preferences", () => {
  writeLeadOfflineData(leadOfflineScope(user, 20), { leads: [lead], queue: [note] });
  writeLeadOfflineData(leadOfflineScope({ ...user, id: 2 }, 21), empty);
  localStorage.setItem("zani_leads_cache", "old");
  localStorage.setItem("zani_leads_offline_queue", "old");
  localStorage.setItem("zani_leads_columns", "preferences");
  clearLeadOfflineStorage();
  assert.equal(localStorage.length, 1);
  assert.equal(localStorage.getItem("zani_leads_columns"), "preferences");
});
test("malformed or unavailable storage fails closed without breaking the workspace or logout", () => {
  const scope = leadOfflineScope(user, 20);
  localStorage.setItem(scope.key, "{");
  assert.deepEqual(readLeadOfflineData(scope), empty);
  globalThis.localStorage = new Proxy({}, { get() { throw new Error("Storage denied"); } });
  assert.deepEqual(readLeadOfflineData(scope), empty);
  assert.doesNotThrow(() => writeLeadOfflineData(scope, { leads: [lead], queue: [] }));
  assert.doesNotThrow(clearLeadOfflineStorage);
});
