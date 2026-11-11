import test from "node:test";
import assert from "node:assert/strict";
import { comparisonChange, includePreviousGroups } from "../../src/features/analytics/comparisonValues.ts";

test("positive baselines yield signed absolute and relative changes", () => {
  assert.deepEqual(comparisonChange(12, 10), { absolute: 2, percent: 20 });
  assert.deepEqual(comparisonChange(0, 10), { absolute: -10, percent: -100 });
  assert.deepEqual(comparisonChange(33.3, 33.1), { absolute: 0.2, percent: 0.6 });
});
test("zero is a valid count but not a percentage growth baseline; missing stays missing", () => {
  assert.deepEqual(comparisonChange(0, 0), { absolute: 0, percent: null });
  assert.deepEqual(comparisonChange(5, 0), { absolute: 5, percent: null });
  assert.equal(comparisonChange(null, 0), null);
  assert.equal(comparisonChange(5, null), null);
});
test("groups that disappear remain visible as current zero without duplicating active groups", () => {
  const prior = [{ id: 1, total: 5 }, { id: 2, total: 9 }];
  assert.deepEqual(includePreviousGroups([{ id: 1, total: 3 }], prior, row => row.id, row => ({ ...row, total: 0 })),
    [{ id: 1, total: 3 }, { id: 2, total: 0 }]);
  assert.equal(prior[1].total, 9);
});
