import assert from "node:assert/strict";
import test from "node:test";
import { scheduleCell, shiftDate, validDate, weekDates, weekdayOf } from "../../src/features/business/schedule.ts";

const config = { days: [], assignments: [], offers: [], physical_resources: [], resource_requirements: [], travel: [], absences: [] };
const cell = overrides => scheduleCell({ automatic: false, config, hours: [], exceptions: [], resource: 12, date: "2030-01-07", ...overrides });
const interval = { start: "09:00", end: "18:00" };

test("week navigation keeps ISO dates over month, leap year and year boundaries", () => {
  assert.equal(shiftDate("2028-02-28", 1), "2028-02-29");
  assert.equal(shiftDate("2030-01-01", -1), "2029-12-31");
  assert.equal(weekdayOf("2030-01-07"), 0);
  assert.deepEqual(weekDates("2030-01-13"), ["2030-01-07", "2030-01-08", "2030-01-09", "2030-01-10", "2030-01-11", "2030-01-12", "2030-01-13"]);
});

test("invalid URL dates recover without silently normalizing impossible calendar dates", () => {
  for (const date of [null, "", "bad", "2030-02-30", "2030-13-01"]) assert.equal(validDate(date, "2030-01-07"), "2030-01-07");
  assert.equal(validDate("2028-02-29", "2030-01-07"), "2028-02-29");
});

test("explicit day off overrides a working week without losing its identity", () => {
  const data = { ...config, days: [{ resource: 12, weekday: 0, date: null, intervals: [interval] }, { resource: 12, weekday: null, date: "2030-01-07", intervals: [] }] };
  assert.deepEqual(cell({ config: data }), { intervals: [], override: true, configured: true, absent: false });
  assert.deepEqual(cell({ config: data, date: "2030-01-14" }).intervals, [interval]);
  assert.equal(cell({ config: data, resource: 99 }).configured, false);
});

test("automatic hours fall back to business only when individual hours are missing", () => {
  const hours = [{ resource: null, weekday: 0, start_time: "09:00:00", end_time: "18:00:00", is_day_off: false }, { resource: 12, weekday: 0, is_day_off: true }];
  assert.deepEqual(cell({ automatic: true, hours }).intervals, []);
  assert.deepEqual(cell({ automatic: true, hours, resource: 99 }).intervals, [interval]);
});

test("automatic dated override belongs only to its resource and date", () => {
  const hours = [{ resource: null, weekday: 0, start_time: "09:00:00", end_time: "18:00:00", is_day_off: false }];
  const exceptions = [{ resource: 12, date: "2030-01-07", start_time: "11:00:00", end_time: "13:00:00", is_day_off: false }];
  assert.deepEqual(cell({ automatic: true, hours, exceptions }).intervals, [{ start: "11:00", end: "13:00" }]);
  assert.equal(cell({ automatic: true, hours, exceptions, resource: 99 }).override, false);
  assert.equal(cell({ automatic: true, hours, exceptions, date: "2030-01-14" }).override, false);
});

test("absence is separate from the stored schedule and does not mutate it", () => {
  const data = { ...config, days: [{ resource: 12, weekday: 0, date: null, intervals: [interval] }], absences: [{ resource_id: 12, starts_on: "2030-01-07", ends_on: "2030-01-09" }] };
  const before = JSON.stringify(data);
  assert.deepEqual(cell({ config: data }), { intervals: [interval], configured: true, override: false, absent: true });
  assert.equal(cell({ config: data, date: "2030-01-14" }).absent, false);
  assert.equal(cell({ config: data, resource: 99 }).absent, false);
  assert.equal(JSON.stringify(data), before);
});
