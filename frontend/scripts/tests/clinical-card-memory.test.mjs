import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

function load() {
  const exports = {};
  const source = fs.readFileSync(new URL("../../src/features/medical/clinicalCardMemory.ts", import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } });
  vm.runInNewContext(outputText, { exports });
  return exports.clinicalCardMemory;
}

test("closing and reopening a card retains navigation but another appointment starts independently", () => {
  const memory = load();
  const first = memory("20:27", 97);
  first.tab = "teeth";
  first.views.teeth.set("20:1:97:", { mode: "mixed", date: "2000-01-01T12:00", quadrant: 2 });
  assert.equal(memory("20:27", 97), first);
  assert.equal(memory("20:27", 98).tab, "encounter");
  assert.equal(memory("20:27", 98).views.teeth.size, 0);
});

test("switching user or business discards the previous navigation scope", () => {
  const memory = load();
  const first = memory("20:27", 97);
  first.tab = "history";
  assert.equal(memory("20:28", 97).tab, "encounter");
  assert.notEqual(memory("20:27", 97), first);
  memory("20:27", 97).tab = "plan";
  assert.equal(memory("21:27", 97).tab, "encounter");
  assert.equal(memory("20:27", 97).tab, "encounter");
});

test("old card navigation is evicted instead of growing without a bound", () => {
  const memory = load();
  const first = memory("20:27", 1);
  first.tab = "documents";
  for (let id = 2; id <= 33; id++) memory("20:27", id);
  assert.notEqual(memory("20:27", 1), first);
  assert.equal(memory("20:27", 1).tab, "encounter");
});
