import assert from "node:assert/strict";
import test from "node:test";
import { notificationContent, notificationDedupeKey } from "../../src/components/notifications/notificationPolicy.ts";

test("one server request or explicit event has one notification identity", () => {
  const first = { appError: { requestId: "r1", code: "internal_error" } };
  assert.equal(notificationDedupeKey(first), notificationDedupeKey({ ...first, onAction() {} }));
  assert.notEqual(notificationDedupeKey(first), notificationDedupeKey({ appError: { requestId: "r2", code: "internal_error" } }));
  assert.equal(notificationDedupeKey({ dedupeKey: "save:1" }), notificationDedupeKey({ dedupeKey: "save:1", message: "Saved" }));
});

test("title and description preserve legacy fallback and never repeat a line", () => {
  assert.deepEqual(notificationContent({ message: "Saved" }, "Fallback"), { title: "Saved", description: undefined });
  assert.deepEqual(notificationContent({ title: "Saved", message: "Client updated" }, "Fallback"), { title: "Saved", description: "Client updated" });
  assert.deepEqual(notificationContent({ title: "Saved", description: "Details", message: "Old" }, "Fallback"), { title: "Saved", description: "Details" });
  assert.deepEqual(notificationContent({ title: "Saved", description: "Saved" }, "Fallback"), { title: "Saved", description: undefined });
  assert.deepEqual(notificationContent({ title: "Failure", appError: {} }, "Localized error"), { title: "Failure", description: "Localized error" });
  assert.deepEqual(notificationContent({ description: "More" }, "Fallback"), { title: "Fallback", description: "More" });
  assert.deepEqual(notificationContent({}, "Fallback"), { title: "Fallback", description: undefined });
});

test("distinct descriptions and tones retain distinct identities", () => {
  const item = { title: "Saved", description: "First", tone: "success" };
  assert.notEqual(notificationDedupeKey(item), notificationDedupeKey({ ...item, description: "Second" }));
  assert.notEqual(notificationDedupeKey(item), notificationDedupeKey({ ...item, tone: "warning" }));
  assert.equal(notificationDedupeKey({ ...item, onAction() {} }), undefined);
  assert.equal(notificationDedupeKey({ ...item, dedupeKey: "explicit" }), notificationDedupeKey({ description: "Second", dedupeKey: "explicit" }));
});

test("plain duplicate notices collapse without merging unrelated actionable operations", () => {
  assert.equal(notificationDedupeKey({ message: "Saved", tone: "success" }), notificationDedupeKey({ message: "Saved", tone: "success" }));
  assert.notEqual(notificationDedupeKey({ message: "Saved", tone: "success" }), notificationDedupeKey({ message: "Saved", tone: "warning" }));
  assert.equal(notificationDedupeKey({ message: "Failed", onAction() {} }), undefined);
  assert.equal(notificationDedupeKey({ appError: { code: "internal_error" } }), undefined);
});
