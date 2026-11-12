import assert from "node:assert/strict";
import test from "node:test";
import { readWidgetSession, saveWidgetSession, widgetSessionKey } from "../../widget/src/session.ts";

test("reload retains this visitor's conversation, acknowledged messages and draft", () => {
  const data = new Map(), storage = { getItem: key => data.get(key), setItem: (key, value) => data.set(key, value) };
  const key = widgetSessionKey("https://crm.example.invalid/", "public-A", "visitor-A");
  const session = { conversationId: "11111111-1111-1111-1111-111111111111", messages: ["Әлия"], fullName: "QA", phone: "123", draft: "Unsent" };
  saveWidgetSession(storage, key, session);
  assert.deepEqual(readWidgetSession(storage, key), session);
  for (const other of [widgetSessionKey("https://other.example.invalid", "public-A", "visitor-A"), widgetSessionKey("https://crm.example.invalid", "public-B", "visitor-A"), widgetSessionKey("https://crm.example.invalid", "public-A", "visitor-B")]) {
    assert.equal(readWidgetSession(storage, other), null);
  }
});

test("corrupt or blocked storage cannot break chat; retained transcript is bounded", () => {
  assert.equal(readWidgetSession({ getItem() { throw new Error("blocked"); } }, "key"), null);
  assert.doesNotThrow(() => saveWidgetSession({ setItem() { throw new Error("blocked"); } }, "key", { messages: [] }));
  for (const value of ["{", '{"conversationId":"../../wrong","messages":[]}', '{"conversationId":null,"messages":[1]}']) {
    assert.equal(readWidgetSession({ getItem: () => value }, "key"), null);
  }
  const session = readWidgetSession({ getItem: () => JSON.stringify({ conversationId: null, messages: Array(120).fill("kept"), draft: "x".repeat(21000) }) }, "key");
  assert.equal(session.messages.length, 100);
  assert.equal(session.draft.length, 20000);
});
