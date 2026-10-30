import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import vm from "node:vm";
import ts from "typescript";

function load(path, imports) {
  const source = fs.readFileSync(new URL(`../../src/${path}`, import.meta.url), "utf8");
  const exports = {};
  vm.runInNewContext(ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText, { exports, require: name => {
    assert.ok(name in imports, name); return imports[name];
  } });
  return exports;
}
const job = { id: 3, business: 1, entity_type: "leads" };
function fixture() {
  const state = [], options = [], calls = [], cache = [], invalidations = [];
  let cursor = 0, list = { data: { count: 43, results: [job] } }, detail = { data: job };
  const { useImportHistory } = load("features/integrations/components/useImportHistory.ts", {
    react: { useState: initial => { const n = cursor++; if (!(n in state)) state[n] = initial; return [state[n], value => { state[n] = value; }]; } },
    "@tanstack/react-query": {
      useQuery: config => { options.push(config); return options.length === 1 ? list : detail; },
      useQueryClient: () => ({ setQueryData: (...args) => cache.push(args), invalidateQueries: value => invalidations.push(value) }),
    },
    "../../../api/importExport": { importExportApi: {
      importJobs: params => calls.push(params), getImportJob: (id, params) => calls.push({ id, ...params }),
    } },
  });
  return { render(user = 2, business = 1, entity = "leads") { cursor = 0; options.length = 0; return useImportHistory(user, business, entity); },
    options, calls, cache, invalidations, list(value) { list = value; }, detail(value) { detail = value; } };
}

test("server receives entity/business and page; changing size returns to first page", () => {
  const f = fixture(); let h = f.render(); h.changePage(3); h = f.render(); f.options[0].queryFn();
  assert.equal(f.calls[0].page, 3); assert.equal(f.calls[0].page_size, 20);
  assert.equal(f.calls[0].business, 1); assert.equal(f.calls[0].entity_type, "leads");
  h.changePageSize(50); h = f.render(); assert.equal(h.page, 1); assert.equal(h.pageSize, 50);
});

test("older selection loads current detail; wrong id/entity/tenant and stale denied data stay hidden", () => {
  const f = fixture(); let h = f.render(); h.select(99); h = f.render();
  f.options[1].queryFn(); assert.equal(f.calls[0].id, 99); assert.equal(f.calls[0].entity_type, "leads");
  assert.equal(h.selected, undefined);
  for (const data of [{ ...job, id: 99, business: 9 }, { ...job, id: 99, entity_type: "clients" }]) {
    f.detail({ data }); assert.equal(f.render().selected, undefined);
  }
  f.detail({ data: { ...job, id: 99 } }); assert.equal(f.render().selected.id, 99);
  f.detail({ data: { ...job, id: 99 }, isError: true }); assert.equal(f.render().selected, undefined);
  f.detail({ data: { ...job, id: 99 }, isFetching: true }); assert.equal(f.render().selected, undefined);
});

test("history error hides cached rows and detail; recovery restores current results", () => {
  const f = fixture(); f.list({ isError: true, data: { results: [job] } });
  let h = f.render(); assert.equal(h.jobs.length, 0); assert.equal(h.selected, undefined); assert.equal(f.options[1].enabled, false);
  f.list({ data: { count: 43, results: [job] } }); h = f.render(); assert.equal(h.selected.id, job.id);
  assert.equal(f.options[0].retry, false); assert.equal(f.options[1].retry, false);
  assert.equal(f.options[1].refetchOnWindowFocus, false);
});

test("mutation caches only matching job, selects it and resets upload history page", () => {
  const f = fixture(); let h = f.render(); h.changePage(3); h = f.render();
  h.accept({ ...job, business: 8 }, true); assert.equal(f.cache.length, 0);
  h.accept({ ...job, id: 80 }, true); h = f.render(); assert.equal(h.page, 1); assert.equal(h.selectedId, 80);
  assert.equal(f.cache.length, 1); assert.equal(f.invalidations.length, 1);
  h.changePage(2); h = f.render(); assert.equal(h.selectedId, job.id);
});

test("list and detail cache keys isolate user, business and entity", () => {
  const f = fixture(); f.render(); const first = JSON.stringify(f.options.map(o => o.queryKey));
  for (const args of [[9, 1, "leads"], [2, 8, "leads"], [2, 1, "clients"]]) {
    f.render(...args); assert.notEqual(JSON.stringify(f.options.map(o => o.queryKey)), first);
  }
});

test("API retains page count and passes detail context to backend", async () => {
  const calls = []; const page = { count: 43, results: [job] };
  const { importExportApi } = load("api/importExport.ts", { "./client": { apiClient: { get: async (...args) => { calls.push(args); return { data: page }; } } } });
  assert.equal(await importExportApi.importJobs({ business: 1, entity_type: "leads", page: 3, page_size: 20 }), page);
  await importExportApi.getImportJob(99, { business: 1, entity_type: "leads" });
  assert.equal(calls[1][0], "/api/import-jobs/99/"); assert.equal(calls[1][1].params.business, 1);
});

test("pagination keeps portal default for tables and supports modal-local size selection", () => {
  const element = (type, props) => ({ type, props });
  const { CrmPagination } = load("components/crm/CrmPagination.tsx", {
    "react/jsx-runtime": { jsx: element, jsxs: element }, "lucide-react": { ChevronLeft: "Left", ChevronRight: "Right" },
    "../../lib/cn": { cn: (...args) => args.filter(Boolean).join(" ") }, "../ui/Select": { Select: "Select" },
    "../../lib/i18n": { useI18n: () => ({ t: key => key }) },
  });
  function nodes(value) { if (!value || typeof value !== "object") return []; if (Array.isArray(value)) return value.flatMap(nodes); return [value, ...nodes(value.props?.children)]; }
  const pages = [], sizes = [];
  const props = { compact: true, shown: 3, total: 43, page: 3, pageSize: 20, onPageChange: v => pages.push(v), onPageSizeChange: v => sizes.push(v) };
  assert.equal(nodes(CrmPagination(props)).find(n => n.type === "Select").props.portal, true);
  const select = nodes(CrmPagination({ ...props, pageSizePortal: false })).find(n => n.type === "Select");
  assert.equal(select.props.portal, false); select.props.onChange({ target: { value: "10" } });
  assert.deepEqual(pages, [1]); assert.deepEqual(sizes, [10]);
});
