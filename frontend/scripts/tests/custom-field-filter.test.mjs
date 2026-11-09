import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import test from "node:test";
import ts from "typescript";

function load(file, modules = {}) {
  const source = fs.readFileSync(new URL(`../../src/${file}`, import.meta.url), "utf8");
  const exports = {};
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
  vm.runInNewContext(code, { exports, require: name => {
    if (!(name in modules)) throw new Error(`Unexpected dependency: ${name}`);
    return modules[name];
  } });
  return exports;
}

const { validCustomFieldFilter } = load("components/crm/CustomFieldFilterFields.tsx", {
  "react/jsx-runtime": {}, "../../lib/i18n": {}, "../ui/Input": {}, "../ui/Select": {},
  "../../lib/customFields": load("lib/customFields.ts"),
});
const definitions = [{ id: 1, field_type: "multiselect", options_json: { display: { in_filters: true }, options: ["A", { value: "B", label: "Second" }] } }];
const selection = (custom_value, custom_operator = "equals") => ({ custom_field: "1", custom_value, custom_operator });

test("multiselect filter accepts allowed selections and rejects malformed or stale URL values", () => {
  for (const value of ['["A"]', '["A","B"]', "A"]) assert.equal(validCustomFieldFilter(selection(value), definitions), true, value);
  for (const value of ["", "[]", '["missing"]', "[1]", '["A"']) assert.equal(validCustomFieldFilter(selection(value), definitions), false, value);
  assert.equal(validCustomFieldFilter(selection('["A"]', "gte"), definitions), false);
  assert.equal(validCustomFieldFilter(selection("", "is_empty"), definitions), true);
  assert.equal(validCustomFieldFilter(selection('["A"]'), []), false);
  assert.equal(validCustomFieldFilter(selection('["A"]'), [{ ...definitions[0], options_json: { display: { in_filters: false } } }]), false);
});

test("scalar filters retain zero and false while refusing blank comparison values", () => {
  for (const [field_type, value, operator] of [["number", "0", "gte"], ["boolean", "false", "equals"], ["date", "2026-11-09", "lte"]]) {
    const fields = [{ id: 1, field_type, options_json: { display: { in_filters: true } } }];
    assert.equal(validCustomFieldFilter(selection(value, operator), fields), true);
    assert.equal(validCustomFieldFilter(selection("  ", operator), fields), false);
  }
});
