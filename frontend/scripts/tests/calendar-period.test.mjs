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
vm.runInNewContext(outputText, { exports, require: () => ({ viewModes: ["week", "month", "year"] }) });
const { shiftCalendarPeriod, formatCalendarPeriod, getQueryView, getCalendarRange, getMonthDates, toDateInputValue } = exports;

test("arrows advance the selected week or month across year boundaries", () => {
  assert.equal(shiftCalendarPeriod("2026-12-31", 1, "week"), "2027-01-07");
  assert.equal(shiftCalendarPeriod("2026-01-01", -1, "week"), "2025-12-25");
  assert.equal(shiftCalendarPeriod("2026-12-31", 1, "month"), "2027-01-31");
  assert.equal(shiftCalendarPeriod("2026-01-31", 1, "month"), "2026-02-28");
  assert.equal(shiftCalendarPeriod("2028-03-31", -1, "month"), "2028-02-29");
  assert.equal(shiftCalendarPeriod("2026-03-31", -1, "month"), "2026-02-28");
  assert.equal(shiftCalendarPeriod("2028-02-29", 1, "year"), "2029-02-28");
  assert.equal(shiftCalendarPeriod("2026-11-04", -1, "year"), "2025-11-04");
});

test("period label represents the displayed range in every supported locale", () => {
  for (const locale of ["ru", "kk", "en"]) {
    assert.match(formatCalendarPeriod("2026-12-31", locale, "week"), /2026/);
    assert.match(formatCalendarPeriod("2026-12-31", locale, "week"), /2027/);
    assert.doesNotMatch(formatCalendarPeriod("2026-10-08", locale, "month"), /08/);
    assert.match(formatCalendarPeriod("2030-10-08", locale, "year"), /2030/);
  }
});

test("legacy day/list links retain their date in the month workspace", () => {
  for (const value of [null, "day", "list", "invalid"]) assert.equal(getQueryView(value), "month");
  assert.equal(getQueryView("week"), "week");
  assert.equal(getQueryView("month"), "month");
  assert.equal(getQueryView("year"), "year");
  assert.deepEqual(JSON.parse(JSON.stringify(getCalendarRange("2026-12-31", "week"))), { start: "2026-12-28", end: "2027-01-04" });
  assert.deepEqual(JSON.parse(JSON.stringify(getCalendarRange("2028-02-29", "month"))), { start: "2028-01-31", end: "2028-03-06" });
});

test("visible month includes real adjacent dates and fetches the same exclusive range", () => {
  for (let month = 1; month <= 12; month++) {
    const date = `2026-${String(month).padStart(2, "0")}-15`;
    const cells = getMonthDates(date);
    assert.equal(cells.length % 7, 0);
    assert.equal(cells[0].getDay(), 1);
    assert.equal(cells.at(-1).getDay(), 0);
    assert.equal(new Set(cells.map(toDateInputValue)).size, cells.length);
    assert.equal(getCalendarRange(date, "month").start, toDateInputValue(cells[0]));
    assert.equal(exports.shiftDateValue(toDateInputValue(cells.at(-1)), 1), getCalendarRange(date, "month").end);
  }
  const november = getMonthDates("2026-11-04");
  assert.equal(toDateInputValue(november[0]), "2026-10-26");
  assert.equal(toDateInputValue(november.at(-1)), "2026-12-06");
});

test("year ranges include leap day and arbitrary past/future years", () => {
  for (const year of [2020, 2028, 2030]) {
    const range = getCalendarRange(`${year}-06-01`, "year");
    assert.equal(range.start, `${year}-01-01`);
    assert.equal(range.end, `${year + 1}-01-01`);
  }
});
