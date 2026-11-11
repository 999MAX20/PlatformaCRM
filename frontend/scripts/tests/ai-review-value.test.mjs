import test from "node:test";
import assert from "node:assert/strict";
import { reviewValue } from "../../src/features/assistant/reviewValue.ts";
const review = { timezone: "Asia/Qyzylorda", values: { client: "Client name", service: null }, before: { client: "Previous client" } };
test("scoped relation labels and unavailable values replace IDs on both sides", () => {
  assert.equal(reviewValue("client", 5, "values", review, "en", "Unavailable"), "Client name");
  assert.equal(reviewValue("client", 4, "before", review, "en", "Unavailable"), "Previous client");
  assert.equal(reviewValue("service", 99, "values", review, "en", "Unavailable"), "Unavailable");
  assert.equal(reviewValue("client", null, "before", review, "en", "Unavailable"), "—");
});
test("dates show the business time in all supported locales; malformed values remain visible", () => {
  for (const language of ["ru", "kk", "en"]) {
    assert.match(reviewValue("start_at", "2026-11-20T05:30:00Z", "values", review, language, ""), /10:30/);
  }
  assert.equal(reviewValue("start_at", "invalid", "values", review, "en", ""), "invalid");
  assert.equal(reviewValue("title", "Task", "values", review, "en", ""), "Task");
});
