import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import test from "node:test";
import ts from "typescript";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

// Exercise the actual component schemas without loading their UI/API dependencies.
function componentSchema(name) {
  const file = new URL(`../../src/components/forms/${name}.tsx`, import.meta.url);
  const source = fs.readFileSync(file, "utf8");
  const ast = ts.createSourceFile(file.pathname, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const declarations = ast.statements.filter(node =>
    (ts.isFunctionDeclaration(node) && node.name?.text === "createSchema") ||
    (ts.isVariableStatement(node) && node.declarationList.declarations.some(item =>
      ts.isIdentifier(item.name) && ["createSchema", "schema"].includes(item.name.text))));
  assert.equal(declarations.length, 1, `${name} must expose one schema declaration to this test`);
  const code = declarations.map(node => node.getText(ast)).join("\n");
  const compiled = ts.transpileModule(code, { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText;
  return vm.runInNewContext(`${compiled}\n(typeof createSchema === 'function' ? createSchema(key => key) : schema)`, { z });
}

const cases = [
  { name: "AppointmentForm", valid: { client: "11", service: "12", resource: "13", lead: "", date: "2026-11-02", slot: "2026-11-02T10:00:00Z", source: "manual" }, numbers: { client: 11, service: 12, resource: 13, lead: 0 }, field: "client", invalid: "0" },
  { name: "LeadForm", valid: { client: "11", service: "", source: "manual", responsible_user: "" }, numbers: { client: 11, service: 0, responsible_user: 0 }, field: "client", invalid: "0" },
  { name: "ServiceForm", valid: { name: "Synthetic service", duration_minutes: "45", price_from: "1200" }, numbers: { duration_minutes: 45 }, field: "duration_minutes", invalid: "14" },
  { name: "WorkingHoursForm", valid: { resource: "", weekday: "0", start_time: "09:00", end_time: "18:00", is_day_off: false }, numbers: { resource: 0, weekday: 0 }, field: "weekday", invalid: "7" },
];

for (const item of cases) {
  const resolver = zodResolver(componentSchema(item.name));
  const resolve = values => resolver(values, undefined, { criteriaMode: "all", fields: {}, shouldUseNativeValidation: false });
  test(`${item.name}: DOM strings are coerced and numeric defaults still work`, async () => {
    for (const input of [item.valid, { ...item.valid, ...item.numbers }]) {
      const result = await resolve(input);
      assert.deepEqual(result.errors, {});
      for (const [field, value] of Object.entries(item.numbers)) assert.equal(result.values[field], value);
    }
  });
  test(`${item.name}: invalid range and malformed number reject submission; corrected input recovers`, async () => {
    for (const value of [item.invalid, "not-a-number"]) {
      const result = await resolve({ ...item.valid, [item.field]: value });
      assert.deepEqual(result.values, {});
      assert.ok(result.errors[item.field]?.message);
    }
    assert.deepEqual((await resolve(item.valid)).errors, {});
  });
}
