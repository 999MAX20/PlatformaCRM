import assert from "node:assert/strict";
import test from "node:test";
import { captureFieldOptions, captureOptionsPatch } from "../../src/features/leads/utils/captureFieldOptions.ts";

test("editing a field label leaves existing option metadata untouched", () => {
  const metadata = { options: [{ value: "call", label: "Call back", routing: "sales" }, "email"], custom: true };
  assert.deepEqual(captureFieldOptions(metadata).map(option => option.value), ["call", "email"]);
  assert.equal(captureOptionsPatch(metadata, ["call", "email"]), undefined);
});

test("changing choices preserves surviving option labels and unrelated metadata", () => {
  const option = { key: "call", label: "Call back", routing: "sales" };
  const metadata = { options: [option, "email"], custom: { source: "form" } };
  assert.deepEqual(captureOptionsPatch(metadata, ["visit", "call"]), {
    options: ["visit", option], custom: { source: "form" },
  });
  assert.deepEqual(metadata.options, [option, "email"]);
  assert.deepEqual(captureOptionsPatch(undefined, ["new"]), { options: ["new"] });
});
