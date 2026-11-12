import assert from "node:assert/strict";
import test from "node:test";
import { deliveryNotice } from "../../src/features/conversations/deliveryNotice.ts";

test("delivery feedback only claims sent for a confirmed sent response", () => {
  assert.deepEqual(deliveryNotice("sent"), { key: "conversations.replySent", tone: "success" });
  assert.deepEqual(deliveryNotice("failed"), { key: "conversations.deliveryStatusFailed", tone: "warning" });
  assert.deepEqual(deliveryNotice("delivery_unknown"), { key: "conversations.deliveryYCloudUnknown", tone: "warning" });
  assert.equal(deliveryNotice("accepted").tone, "info");
  for (const status of ["queued", "sending", "retry_scheduled", "unknown"]) {
    assert.deepEqual(deliveryNotice(status), { key: "conversations.deliveryStatusQueued", tone: "info" });
  }
});
