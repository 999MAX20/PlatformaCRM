import assert from "node:assert/strict";
import test from "node:test";
import { notificationDedupeKey } from "../../src/components/notifications/notificationPolicy.ts";

test("one server request or explicit event has one notification identity", () => {
  const first = { appError: { requestId: "r1", code: "internal_error" } };
  assert.equal(notificationDedupeKey(first), notificationDedupeKey({ ...first, onAction() {} }));
  assert.notEqual(notificationDedupeKey(first), notificationDedupeKey({ appError: { requestId: "r2", code: "internal_error" } }));
  assert.equal(notificationDedupeKey({ dedupeKey: "save:1" }), notificationDedupeKey({ dedupeKey: "save:1", message: "Saved" }));
});

test("plain duplicate notices collapse without merging unrelated actionable operations", () => {
  assert.equal(notificationDedupeKey({ message: "Saved", tone: "success" }), notificationDedupeKey({ message: "Saved", tone: "success" }));
  assert.notEqual(notificationDedupeKey({ message: "Saved", tone: "success" }), notificationDedupeKey({ message: "Saved", tone: "warning" }));
  assert.equal(notificationDedupeKey({ message: "Failed", onAction() {} }), undefined);
  assert.equal(notificationDedupeKey({ appError: { code: "internal_error" } }), undefined);
});
