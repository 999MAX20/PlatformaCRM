import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = await readFile(new URL("../../src/features/calendar/calendarUtils.ts", import.meta.url), "utf8");
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
});
const exports = {};
vm.runInNewContext(outputText, { exports, require: () => ({}) });
const { shiftCalendarPeriod, formatCalendarPeriod } = exports;

test("arrows advance the selected day, week or month across year boundaries", () => {
  assert.equal(shiftCalendarPeriod("2026-12-31", 1, "day"), "2027-01-01");
  assert.equal(shiftCalendarPeriod("2026-12-31", 1, "week"), "2027-01-07");
  assert.equal(shiftCalendarPeriod("2026-01-01", -1, "week"), "2025-12-25");
  assert.equal(shiftCalendarPeriod("2026-12-31", 1, "month"), "2027-01-31");
  assert.equal(shiftCalendarPeriod("2026-01-31", 1, "month"), "2026-02-28");
  assert.equal(shiftCalendarPeriod("2028-03-31", -1, "month"), "2028-02-29");
  assert.equal(shiftCalendarPeriod("2026-03-31", -1, "month"), "2026-02-28");
  assert.equal(shiftCalendarPeriod("2026-10-08", 1, "list"), "2026-10-09");
});

test("period label represents the displayed range in every supported locale", () => {
  for (const locale of ["ru", "kk", "en"]) {
    assert.match(formatCalendarPeriod("2026-12-31", locale, "week"), /2026/);
    assert.match(formatCalendarPeriod("2026-12-31", locale, "week"), /2027/);
    assert.doesNotMatch(formatCalendarPeriod("2026-10-08", locale, "month"), /08/);
    assert.match(formatCalendarPeriod("2026-10-08", locale, "day"), /08/);
  }
});
