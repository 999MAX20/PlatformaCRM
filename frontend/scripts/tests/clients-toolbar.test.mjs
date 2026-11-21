import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import test from "node:test";
import ts from "typescript";

function load(file, modules) {
  const code = ts.transpileModule(fs.readFileSync(new URL(`../../src/${file}`, import.meta.url), "utf8"), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
  const exports = {};
  vm.runInNewContext(code, { exports, require: name => { if (!(name in modules)) throw new Error(name); return modules[name]; }, URLSearchParams });
  return exports;
}
function filters(query, kind = "clients") {
  let params = new URLSearchParams(query);
  const hook = load("components/crm/useCrmFilters.ts", {
    react: { useMemo: fn => fn(), useCallback: fn => fn },
    "react-router": { useSearchParams: () => [params, change => { params = change(params); }] },
  });
  return { hook, run: () => hook.useCrmFilters(kind), params: () => params };
}

test("client draft applies native and additional fields atomically, clears paging and preserves card context", () => {
  const f = filters("search=Ali&page=3&client=7&tab=notes&page_size=50");
  f.run().update({ source: "website", custom_field: "9", custom_operator: "contains", custom_value: "Gold" });
  assert.equal(f.params().get("source"), "website");
  assert.equal(f.params().get("custom_field"), "9");
  assert.equal(f.params().get("custom_value"), "Gold");
  assert.equal(f.params().get("page"), null);
  assert.equal(f.params().get("client"), "7");
  assert.equal(f.params().get("page_size"), "50");
  assert.equal(f.run().hasFilters, true);
});

test("reset clears additional fields as well as ordinary client conditions", () => {
  const f = filters("source=website&quick=no_reply&custom_field=8&custom_operator=equals&custom_value=Silver&page=2&create=1");
  f.run().reset();
  assert.equal(f.params().toString(), "create=1");
  assert.equal(f.run().hasFilters, false);
});

test("client URL restores custom filter and sends zero to the server; empty operator drops stale value", () => {
  const f = filters("search=Alpha&source=manual&custom_field=8&custom_operator=gte&custom_value=0");
  assert.equal(f.run().state.custom_field, "8");
  assert.equal(f.hook.crmFilterParams("clients", f.run().state).custom_value, "0");
  f.run().update({ custom_operator: "is_empty" });
  assert.equal(f.params().has("custom_value"), false);
  assert.equal(f.params().get("source"), "manual");
  assert.equal(f.params().get("search"), "Alpha");
});

test("clearing a selected additional field drops its operator and value", () => {
  const f = filters("custom_field=8&custom_operator=contains&custom_value=Private");
  f.run().update({ custom_field: "" });
  assert.equal(f.params().toString(), "");
});

test("saved client view keys retain additional conditions; leads keep their existing contract", () => {
  const f = filters("");
  assert.ok(f.hook.crmFilterKeysFor("clients").includes("custom_value"));
  assert.equal(f.hook.crmFilterKeysFor("leads").includes("custom_value"), false);
  const leads = filters("scope=mine&statuses=lost&page=2", "leads");
  leads.run().update({ quick: "attention" });
  assert.equal(leads.run().state.statuses, "new,contacted,in_progress");
  assert.equal(leads.run().state.scope, "mine");
});

test("unanswered toggle is mutually compatible with current unarchived clients", () => {
  const f = filters("archive=archived");
  f.run().update({ quick: "no_reply", archive: "active" });
  const api = f.hook.crmFilterParams("clients", f.run().state);
  assert.equal(api.quick_filter, "no_reply");
  assert.equal(api.archive, "active");
  f.run().update({ archive: "archived" });
  assert.equal(f.run().state.quick, "all");
});

const fields = load("components/crm/CustomFieldFilterFields.tsx", {
  "react/jsx-runtime": {}, "../../lib/i18n": {}, "../ui/Input": {}, "../ui/Select": {},
  "../../lib/customFields": load("lib/customFields.ts", {}),
});
const definitions = [{ id: 8, field_type: "number", options_json: { display: { in_filters: true } } }];
test("additional-filter draft rejects missing/unavailable definitions and incompatible conditions", () => {
  assert.equal(fields.validCustomFieldFilter({}, definitions), true);
  for (const value of [{ custom_field: "9", custom_value: "4" }, { custom_field: "8", custom_operator: "contains", custom_value: "4" }, { custom_field: "8", custom_value: "  " }]) assert.equal(fields.validCustomFieldFilter(value, definitions), false);
  assert.equal(fields.validCustomFieldFilter({ custom_field: "8", custom_operator: "gte", custom_value: "0" }, definitions), true);
  assert.equal(fields.validCustomFieldFilter({ custom_field: "8", custom_operator: "is_empty" }, definitions), true);
});
