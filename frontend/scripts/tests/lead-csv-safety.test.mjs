import assert from "node:assert/strict";
import fs from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import test from "node:test";
import vm from "node:vm";

const source = fs.readFileSync(new URL("../../src/features/leads/utils/leadExport.ts", import.meta.url), "utf8");
const actual = source.match(/export function toCsvValue\(value: unknown\) \{[\s\S]*?\n\}/)?.[0];
assert.ok(actual);
const toCsvValue = vm.runInNewContext(`${stripTypeScriptTypes(actual).replace("export function", "function")}\ntoCsvValue`);

test("lead CSV cells follow the existing server formula-prefix safety contract", () => {
  for (const value of ["=1+1", "+77010000003", "-2+3", "@SUM(1)", " \t=1+1", "\r\n+123"]) {
    assert.equal(toCsvValue(value), `"'${value}"`);
  }
});

test("lead CSV preserves ordinary text and quotes embedded separators correctly", () => {
  assert.equal(toCsvValue('Client, "A"'), '"Client, ""A"""');
  assert.equal(toCsvValue("First\nSecond"), '"First\nSecond"');
  assert.equal(toCsvValue(null), '""');
  assert.equal(toCsvValue(123), '"123"');
});
