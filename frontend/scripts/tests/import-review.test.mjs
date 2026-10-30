import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import vm from "node:vm";
import ts from "typescript";

function load(relative, imports = {}) {
  const source = fs.readFileSync(new URL(`../../src/${relative}`, import.meta.url), "utf8");
  const compiled = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  const exports = {};
  vm.runInNewContext(compiled, { exports, require: name => {
    assert.ok(name in imports, `Unexpected dependency ${name}`); return imports[name];
  } });
  return exports;
}
const model = load("features/integrations/components/importReviewModel.ts");
const job = { id: 1, business: 2, updated_at: "v1", status: "previewed", mapping_json: { full_name: "Name" }, mapping_fields: ["full_name"],
  preview_json: { headers: ["Name", "Corrected"], rows: [{ Name: "Example" }] }, summary_json: { ready: true }, errors_json: { count: 0 }, total_rows: 1 };

test("confirmation needs a successful current preview, unchanged mapping and no pending or failed request", () => {
  assert.equal(model.canConfirmImport(job, { full_name: "Name" }, false, false), true);
  for (const args of [
    [job, { full_name: "Corrected" }, false, false], [job, {}, false, false],
    [job, job.mapping_json, true, false], [job, job.mapping_json, false, true],
    [{ ...job, status: "imported" }, job.mapping_json, false, false],
    [{ ...job, summary_json: { ready: false } }, job.mapping_json, false, false],
    [{ ...job, errors_json: { count: 61 } }, job.mapping_json, false, false],
  ]) assert.equal(model.canConfirmImport(...args), false);
});

const element = (type, props) => ({ type, props });
function nodes(value) {
  if (!value || typeof value !== "object") return [];
  if (Array.isArray(value)) return value.flatMap(nodes);
  return [value, ...nodes(value.props?.children)];
}
function reviewFixture() {
  let cursor = 0; const state = [], mutations = [], effects = [], calls = [], changes = [], imported = [];
  const imports = {
    react: {
      useState: initial => { const n = cursor++; if (!(n in state)) state[n] = initial; return [state[n], value => { state[n] = value; }]; },
      useRef: value => { const n = cursor++; return state[n] ||= { current: value }; },
      useEffect: callback => { effects.push(callback); },
    },
    "react/jsx-runtime": { jsx: element, jsxs: element },
    "@tanstack/react-query": { useMutation: config => { mutations.push(config); return { mutate: () => config.mutationFn(), isPending: false }; } },
    "../../../api/importExport": { importExportApi: { preview: (id, mapping) => calls.push({ id, mapping }), confirm: id => calls.push({ id }) } },
    "../../../components/ui/Button": { Button: "Button" }, "../../../components/ui/Select": { Select: "Select" },
    "../../../components/ui/StateViews": { ErrorState: "ErrorState" }, "../../../components/ui/StatusNotice": { StatusNotice: "StatusNotice" },
    "../../../lib/i18n": { useI18n: () => ({ t: key => key }) }, "./ImportErrors": { ImportErrors: "Errors" }, "./importReviewModel": model,
  };
  const { ImportJobReview } = load("features/integrations/components/ImportJobReview.tsx", imports);
  return { render(canCreate = true) { cursor = 0; mutations.length = 0; return nodes(ImportJobReview({ job, userId: 4, canCreate, onChange: result => changes.push(result), onImported: result => imported.push(result) })); }, mutations, effects, calls, changes, imported };
}

test("changing a mapping blocks confirm and sends the selected header to preview", () => {
  const f = reviewFixture(); let tree = f.render();
  tree.find(node => node.type === "Select").props.onChange({ target: { value: "Corrected" } });
  tree = f.render();
  assert.equal(tree.find(node => node.props?.["data-testid"] === "import-confirm").props.disabled, true);
  tree.find(node => node.props?.["data-testid"] === "import-repreview").props.onClick();
  assert.equal(f.calls[0].id, 1); assert.equal(f.calls[0].mapping.full_name, "Corrected");
  assert.equal(f.calls.length, 1); // Preview never automatically confirms.
});

test("late mutation results after leaving the job cannot replace current context", () => {
  const f = reviewFixture(); f.render();
  const cleanup = f.effects[0](); cleanup();
  f.mutations[0].onSuccess({ id: 1 }); f.mutations[1].onSuccess({ id: 1 });
  assert.equal(f.changes.length, 0); assert.equal(f.imported.length, 0);
});

test("read-only role sees mapping without mutation controls", () => {
  const f = reviewFixture(); const tree = f.render(false);
  assert.equal(tree.find(node => node.type === "Select").props.disabled, true);
  assert.equal(tree.some(node => node.props?.["data-testid"] === "import-confirm"), false);
  assert.equal(tree.some(node => node.props?.["data-testid"] === "import-repreview"), false);
});

test("API sends mapping only and requests error page explicitly", async () => {
  const calls = [];
  const { importExportApi } = load("api/importExport.ts", { "./client": { apiClient: {
    post: async (...args) => { calls.push(args); return { data: job }; },
    get: async (...args) => { calls.push(args); return { data: { count: 61, results: [] } }; },
  } } });
  await importExportApi.preview(5, { amount: "Corrected" });
  assert.equal(calls[0][0], "/api/import-jobs/5/preview/");
  assert.deepEqual(Object.keys(calls[0][1]), ["mapping"]);
  await importExportApi.errors(5, 4, 20);
  assert.equal(calls[1][1].params.page, 4); assert.equal(calls[1][1].params.page_size, 20);
});
