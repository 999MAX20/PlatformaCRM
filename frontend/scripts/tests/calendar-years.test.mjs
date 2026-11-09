import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = await readFile(new URL("../../src/components/ui/calendarYears.ts", import.meta.url), "utf8");
const exports = {};
vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, { exports });
const years = (...args) => Array.from(exports.calendarYears(...args));

test("default quick years follow today without a 1900 floor", () => {
  assert.deepEqual(years("2026-11-04", 2026, []), Array.from({ length: 11 }, (_, i) => 2021 + i));
});
test("imported history and future records expand the quick range", () => {
  const result = years("2026-11-04", 2026, [], { from: 2014, to: 2040 });
  assert.equal(result[0], 2014); assert.equal(result.at(-1), 2040);
});
test("explicit historical selections and month navigation stay reachable", () => {
  const result = years("2026-11-04", 1998, ["1985-06-12", "2050-01-01"], { from: 2026, to: 2031 });
  assert.equal(result[0], 1985); assert.equal(result.at(-1), 2050);
});
test("real input validation bounds take precedence over quick suggestions", () => {
  assert.deepEqual(years("2026-11-04", 2026, ["2025-01-01"], undefined, "2027-01-01", "2028-12-31"), [2027, 2028]);
});
