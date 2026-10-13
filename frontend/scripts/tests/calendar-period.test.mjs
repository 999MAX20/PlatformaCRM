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
vm.runInNewContext(outputText, { exports, require: () => ({ viewModes: ["week", "month"] }) });
const { shiftCalendarPeriod, formatCalendarPeriod, getQueryView, getCalendarRange } = exports;

test("arrows advance the selected week or month across year boundaries", () => {
  assert.equal(shiftCalendarPeriod("2026-12-31", 1, "week"), "2027-01-07");
  assert.equal(shiftCalendarPeriod("2026-01-01", -1, "week"), "2025-12-25");
  assert.equal(shiftCalendarPeriod("2026-12-31", 1, "month"), "2027-01-31");
  assert.equal(shiftCalendarPeriod("2026-01-31", 1, "month"), "2026-02-28");
  assert.equal(shiftCalendarPeriod("2028-03-31", -1, "month"), "2028-02-29");
  assert.equal(shiftCalendarPeriod("2026-03-31", -1, "month"), "2026-02-28");
});

test("period label represents the displayed range in every supported locale", () => {
  for (const locale of ["ru", "kk", "en"]) {
    assert.match(formatCalendarPeriod("2026-12-31", locale, "week"), /2026/);
    assert.match(formatCalendarPeriod("2026-12-31", locale, "week"), /2027/);
    assert.doesNotMatch(formatCalendarPeriod("2026-10-08", locale, "month"), /08/);
  }
});

test("legacy day/list links retain their date in the month workspace", () => {
  for (const value of [null, "day", "list", "invalid"]) assert.equal(getQueryView(value), "month");
  assert.equal(getQueryView("week"), "week");
  assert.equal(getQueryView("month"), "month");
  assert.deepEqual(JSON.parse(JSON.stringify(getCalendarRange("2026-12-31", "week"))), { start: "2026-12-28", end: "2027-01-04" });
  assert.deepEqual(JSON.parse(JSON.stringify(getCalendarRange("2028-02-29", "month"))), { start: "2028-02-01", end: "2028-03-01" });
});
