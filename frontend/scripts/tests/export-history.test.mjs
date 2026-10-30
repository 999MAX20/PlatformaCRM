import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import vm from "node:vm";
import ts from "typescript";

function load(path, imports, globals = {}) {
  const exports = {};
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(new URL(`../../src/${path}`, import.meta.url), "utf8"), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText, { exports, ...globals, require: name => { assert.ok(name in imports, name); return imports[name]; } });
  return exports;
}
function nodes(value) {
  if (!value || typeof value !== "object") return [];
  if (Array.isArray(value)) return value.flatMap(nodes);
  return [value, ...nodes(value.props?.children)];
}
const job = { id: 99, kind: "entity", export_key: "leads", created_at: "2026-10-31T00:00:00Z", status: "succeeded", row_count: 3, parameters_json: {}, download_url: "/download" };
function fixture() {
  const state = [], requests = [], downloads = [];
  let cursor = 0, query, result = { data: { count: 43, results: [job] } };
  const jsx = (type, props) => ({ type, props });
  const { ExportHistory } = load("features/analytics/ExportHistory.tsx", {
    "react/jsx-runtime": { jsx, jsxs: jsx },
    react: { useState: initial => { const n = cursor++; if (!(n in state)) state[n] = initial; return [state[n], value => { state[n] = value; }]; } },
    "@tanstack/react-query": {
      useQuery: options => { query = options; return result; },
      useMutation: options => ({ mutate: id => options.mutationFn(id), reset() {} }),
    },
    "../../api/analyticsExports": { analyticsExports: { history: p => requests.push(p), download: (...args) => downloads.push(args) } },
    "../../components/crm/CrmPagination": { CrmPagination: "Pagination" },
    "../../components/ui/Button": { Button: "Button" }, "../../components/ui/Select": { Select: "Select" },
    "../../components/ui/StateViews": { EmptyState: "Empty", ErrorState: "Error", LoadingState: "Loading" },
    "../../lib/i18n": { useI18n: () => ({ t: key => key, language: "en" }) },
  });
  return { render(userId = 2, businessId = 1) { cursor = 0; return nodes(ExportHistory({ userId, business: { id: businessId, timezone: "UTC" } })); },
    query: () => query, result: value => { result = value; }, requests, downloads };
}

test("history preserves server count, pages, filters and actor/Business cache boundaries", () => {
  const f = fixture(); let tree = f.render(); const initial = JSON.stringify(f.query().queryKey);
  const page = tree.find(n => n.type === "Pagination"); assert.equal(page.props.total, 43);
  page.props.onPageChange(3); tree = f.render(); f.query().queryFn(); assert.equal(f.requests.at(-1).page, 3);
  tree.find(n => n.type === "Select").props.onChange({ target: { value: "entity" } });
  f.render(); f.query().queryFn(); assert.equal(f.requests.at(-1).page, 1); assert.equal(f.requests.at(-1).kind, "entity");
  f.render(8); assert.notEqual(JSON.stringify(f.query().queryKey), initial);
  f.render(2, 9); f.query().queryFn(); assert.equal(f.requests.at(-1).business, 9);
});

test("cached rows disappear on error; pending and empty states remain distinct; polling stops on error", () => {
  const f = fixture(); f.result({ error: new Error("503"), data: { count: 43, results: [job] } });
  let tree = f.render(); assert.ok(tree.some(n => n.type === "Error")); assert.ok(!tree.some(n => n.type === "li"));
  assert.equal(f.query().refetchInterval({ state: { error: new Error() } }), false);
  assert.equal(f.query().refetchInterval({ state: {} }), 5000);
  f.result({ isPending: true }); assert.ok(f.render().some(n => n.type === "Loading"));
  f.result({ data: { count: 0, results: [] } }); assert.ok(f.render().some(n => n.type === "Empty"));
  f.result({ data: { count: 43, results: [job] } }); assert.ok(f.render().some(n => n.type === "li"));
});

test("downloads use the selected persisted job and current Business, unavailable files have no button", () => {
  const f = fixture(); let tree = f.render();
  tree.find(n => n.type === "Button" && n.props.children === "analyticsWorkspace.download").props.onClick();
  assert.deepEqual(f.downloads, [[99, 1]]);
  for (const record of [{ ...job, status: "pending" }, { ...job, download_url: null }]) {
    f.result({ data: { count: 1, results: [record] } }); tree = f.render();
    assert.ok(!tree.some(n => n.type === "Button" && n.props.children === "analyticsWorkspace.download"));
  }
});

test("API returns full page and carries history filters without discarding pagination", async () => {
  const page = { count: 43, results: [job] }, calls = [];
  const { analyticsExports } = load("api/analyticsExports.ts", { "./client": { apiClient: { get: async (...args) => { calls.push(args); return { data: page }; } } } });
  assert.equal(await analyticsExports.history({ business: 1, page: 3, page_size: 20, status: "succeeded" }), page);
  assert.equal(calls[0][0], "/api/export-jobs/"); assert.equal(calls[0][1].params.page, 3);
  assert.equal(calls[0][1].params.status, "succeeded");
});
