import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import vm from "node:vm";
import ts from "typescript";

function load(relative, imports) {
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

function hookFixture() {
  const state = []; let cursor = 0, options, response = {}, params;
  const invalidations = [], mutations = [];
  const { useAutomationRuns } = load("features/automations/useAutomationRuns.ts", {
    react: { useState: initial => {
      const slot = cursor++;
      if (!(slot in state)) state[slot] = initial;
      return [state[slot], next => { state[slot] = typeof next === "function" ? next(state[slot]) : next; }];
    } },
    "@tanstack/react-query": {
      useQuery: config => { options = config; return response; },
      useQueryClient: () => ({ invalidateQueries: value => invalidations.push(value) }),
      useMutation: config => { mutations.push(config); return config; },
    },
    "../../api/automations": { automationRunsApi: {
      listPage: async value => { params = value; return {}; }, retry: id => id, cancel: id => id,
    } },
  });
  return {
    render(business = 1, user = 2) { cursor = 0; mutations.length = 0; return useAutomationRuns(business, user); },
    fail() { response = { isError: true }; },
    get options() { return options; }, get params() { return params; }, mutations, invalidations,
  };
}

test("history sends current page/filter/business and resets page on filter changes", async () => {
  const f = hookFixture(); let hook = f.render();
  hook.updateFilters({ page: 4 }); hook = f.render();
  await f.options.queryFn(); assert.equal(f.params.page, 4);
  hook.updateFilters({ status: "failed" }); hook = f.render();
  await f.options.queryFn();
  assert.equal(f.params.page, 1); assert.equal(f.params.status, "failed"); assert.equal(f.params.business, 1);
  hook.updateFilters({ pageSize: 50, triggerType: "lead_created" }); f.render();
  await f.options.queryFn(); assert.equal(f.params.page_size, 50); assert.equal(f.params.trigger_type, "lead_created");
  assert.equal(f.options.retry, false); // Recovery is explicitly reachable in the history block.
});

test("business/user changes isolate cache, selected run and pagination immediately", () => {
  const f = hookFixture(); let hook = f.render();
  hook.updateFilters({ page: 4 }); hook = f.render(); hook.setSelectedRun({ id: 10, business: 1 });
  const firstKey = JSON.stringify(f.options.queryKey);
  hook = f.render(3, 2);
  assert.equal(hook.selectedRun, null); assert.equal(hook.filters.page, 1);
  assert.notEqual(JSON.stringify(f.options.queryKey), firstKey);
  hook.setSelectedRun({ id: 11, business: 3 }); hook = f.render(3, 9);
  assert.equal(hook.selectedRun, null);
  assert.equal(f.options.queryKey[2], 9);
  f.render(null, null); assert.equal(f.options.enabled, false);
});

test("mutation updates open details without opening a different run; errors hide stale details", () => {
  const f = hookFixture(); let hook = f.render(); hook.setSelectedRun({ id: 10, status: "failed" });
  hook = f.render(); f.mutations[0].onSuccess({ id: 10, status: "pending" }); hook = f.render();
  assert.equal(hook.selectedRun.status, "pending"); assert.equal(f.invalidations.length, 1);
  f.mutations[1].onSuccess({ id: 11, status: "cancelled" }); hook = f.render();
  assert.equal(hook.selectedRun.id, 10);
  f.fail(); assert.equal(f.render().selectedRun, null);
});

const element = (type, props) => ({ type, props });
const imports = {
  "react/jsx-runtime": { jsx: element, jsxs: element, Fragment: "Fragment" },
  "./automationPresentation": {
    canCancelRun: run => run.status === "pending", canRetryRun: run => run.status === "failed",
    runStatusVariant: () => "neutral", runStatusLabel: status => status, runStatuses: ["pending", "failed"],
  },
  "lucide-react": { Ban: "Ban", Eye: "Eye", RotateCcw: "RotateCcw" },
  "../../components/ui/Badge": { Badge: "Badge" }, "../../components/ui/Button": { Button: "Button" },
  "../../components/ui/Select": { Select: "Select" },
  "../../components/ui/StateViews": { ErrorState: "ErrorState", LoadingState: "LoadingState" },
  "../../components/crm/CrmPagination": { CrmPagination: "Pagination" },
};
const { AutomationRunList } = load("features/automations/AutomationRunList.tsx", imports);
function nodes(root) {
  if (root == null || typeof root === "boolean") return [];
  if (Array.isArray(root)) return root.flatMap(nodes);
  if (typeof root !== "object") return [root];
  return [root, ...nodes(root.props?.children)];
}
function listFixture(runs, canManage = true) {
  let retried = 0, updated;
  const tree = AutomationRunList({
    t: key => key, runs: { ...runs, refetch: () => retried++ },
    filters: { page: 1, pageSize: 20, status: "", triggerType: "" }, updateFilters: patch => { updated = patch; },
    canManage, triggers: [], locale: "en-US", setSelectedRun() {}, retryRunMutation: {}, cancelRunMutation: {},
  });
  return { nodes: nodes(tree), get retried() { return retried; }, get updated() { return updated; } };
}

test("503 is an error with working retry, never empty history or stale rows", () => {
  const f = listFixture({ isError: true, error: { status: 503 }, data: { results: [{ id: 1 }] } });
  const error = f.nodes.find(x => x.type === "ErrorState");
  assert.ok(error); error.props.action.props.onClick(); assert.equal(f.retried, 1);
  assert.ok(!f.nodes.includes("automations.noRuns")); assert.ok(!f.nodes.some(x => x.props?.["data-testid"] === "automation-run-row"));
});

test("loading and successful empty history are separate", () => {
  const loading = listFixture({ isLoading: true });
  assert.ok(loading.nodes.some(x => x.type === "LoadingState")); assert.ok(!loading.nodes.includes("automations.noRuns"));
  const empty = listFixture({ data: { count: 0, results: [] } });
  assert.ok(empty.nodes.includes("automations.noRuns")); assert.ok(!empty.nodes.some(x => x.type === "ErrorState"));
});

test("all rows of server page render and pagination changes page; viewer cannot mutate", () => {
  const results = Array.from({ length: 20 }, (_, id) => ({ id, status: "failed", created_at: "2026-10-30T10:00:00Z" }));
  const f = listFixture({ data: { count: 107, results } }, false);
  assert.equal(f.nodes.filter(x => x.props?.["data-testid"] === "automation-run-row").length, 20);
  const pagination = f.nodes.find(x => x.type === "Pagination");
  assert.equal(pagination.props.total, 107); pagination.props.onPageChange(2); assert.equal(f.updated.page, 2);
  assert.ok(!f.nodes.includes("automations.retry")); assert.ok(!f.nodes.includes("automations.cancelRun"));
});
