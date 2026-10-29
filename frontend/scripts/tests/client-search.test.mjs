import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import vm from "node:vm";
import ts from "typescript";

// Exercise production hook configuration and event handlers; reachable browser
// coverage additionally verifies React rendering, actual HTTP and focus behavior.
function load(relative, imports, globals = {}) {
  const source = fs.readFileSync(new URL(`../../src/${relative}`, import.meta.url), "utf8");
  const compiled = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  const exports = {};
  vm.runInNewContext(compiled, { exports, require: name => {
    assert.ok(name in imports, `Unexpected dependency ${name}`); return imports[name];
  }, ...globals });
  return exports;
}

function searchFixture({ businessId = 1, userId = 2, allowed = true, term = "old", response = {} } = {}) {
  let config, params;
  const { useClientSearch } = load("hooks/useClientSearch.ts", {
    "@tanstack/react-query": { useInfiniteQuery: options => { config = options; return response; } },
    "../api/clients": { clientsApi: { listFiltered: async input => { params = input; return {}; } } },
    "../features/auth/AuthProvider": { useAuth: () => ({ user: { id: userId } }) },
    "../lib/permissions": { hasPermission: () => allowed },
    "./useBusiness": { useActiveBusiness: () => ({ business: { id: businessId } }) },
    "./useDebouncedValue": { useDebouncedValue: () => term },
  });
  return { run: useClientSearch, config: () => config, params: () => params };
}

test("search is business/user/query scoped and requests only the chosen server page", async () => {
  const first = searchFixture(); first.run("old");
  await first.config().queryFn({ pageParam: 3 });
  assert.equal(JSON.stringify(first.params()), JSON.stringify({ business: 1, q: "old", page: 3, page_size: 20, ordering: "-created_at" }));
  assert.equal(first.config().getNextPageParam({ next: "/api/clients/?page=3" }, [{}, {}]), 3);
  assert.equal(first.config().getNextPageParam({ next: null }, [{}]), undefined);
  const otherUser = searchFixture({ userId: 7 }); otherUser.run("old");
  const otherBusiness = searchFixture({ businessId: 3 }); otherBusiness.run("old");
  assert.notEqual(JSON.stringify(first.config().queryKey), JSON.stringify(otherUser.config().queryKey));
  assert.notEqual(JSON.stringify(first.config().queryKey), JSON.stringify(otherBusiness.config().queryKey));
});

test("denial and changed debounce term never display previously cached client data", () => {
  const response = { data: { pages: [{ clients: [{ id: 9 }] }] } };
  for (const params of [{ allowed: false }, { term: "previous" }, { response: { ...response, isError: true } }]) {
    const fixture = searchFixture({ response, ...params });
    assert.equal(fixture.run("old").clients.length, 0);
    if (params.allowed === false) assert.equal(fixture.config().enabled, false);
  }
  const fixture = searchFixture({ response });
  assert.equal(fixture.run("old").clients[0].id, 9);
  fixture.run("old", false); assert.equal(fixture.config().enabled, false);
});

function selectFixture({ query = "", open = true, options = [], remote, value = "", selectedOption } = {}) {
  const updates = []; let state = 0, focus = 0;
  const jsx = (type, props) => ({ type, props });
  const { SearchableSelect } = load("components/ui/SearchableSelect.tsx", {
    "react/jsx-runtime": { jsx, jsxs: jsx },
    "react": { useEffect() {}, useId: () => "test-id", useMemo: fn => fn(), useRef: () => ({ current: { focus: () => focus++ } }),
      useState: () => { const index = state++; return [index === 0 ? open : query, value => updates.push([index, value])]; } },
    "lucide-react": { Check: "svg", ChevronDown: "svg", Search: "svg", X: "svg" },
    "../../lib/cn": { cn: (...items) => items.filter(Boolean).join(" ") },
    "../../lib/i18n": { useI18n: () => ({ t: key => key }) },
    "./Overlay": { PopoverSurface: "section" }, "./Button": { Button: "button" }, "./StateViews": { ErrorState: "error-state" },
  }, { requestAnimationFrame: fn => fn() });
  const changes = [];
  const tree = SearchableSelect({ value, options, remote, selectedOption, onChange: next => changes.push(next) });
  function nodes(node) {
    if (!node || typeof node !== "object") return [];
    if (Array.isArray(node)) return node.flatMap(nodes);
    return [node, ...nodes(node.props?.children)];
  }
  return { tree, nodes: nodes(tree), changes, updates, focus: () => focus };
}
const options = Array.from({ length: 105 }, (_, i) => ({ value: String(i + 1), label: `Client ${i}` }));
const remote = { onSearch() {}, onOpen() {}, loading: false, error: null, retry() {}, hasMore: false, loadMore() {}, loadingMore: false };

test("server results are not locally re-filtered or truncated at 80; local consumers retain their behavior", () => {
  const server = selectFixture({ options, query: "normalized phone", remote });
  assert.equal(server.nodes.filter(node => node.props?.role === "option").length, 106);
  const local = selectFixture({ options });
  assert.equal(local.nodes.filter(node => node.props?.role === "option").length, 81);
  const searched = selectFixture({ options, query: "Client 104" });
  assert.equal(searched.nodes.filter(node => node.props?.role === "option").length, 2);
});

test("Enter never submits the parent form when loading or empty; a valid result selects and restores focus", () => {
  for (const props of [{ options: [] }, { options, remote: { ...remote, loading: true } }]) {
    const fixture = selectFixture(props); let prevented = false;
    fixture.nodes.find(node => node.type === "input").props.onKeyDown({ key: "Enter", preventDefault: () => { prevented = true; } });
    assert.equal(prevented, true); assert.equal(fixture.changes.length, 0);
  }
  const fixture = selectFixture({ options, remote });
  fixture.nodes.find(node => node.type === "input").props.onKeyDown({ key: "Enter", preventDefault() {} });
  assert.equal(fixture.changes[0], "1"); assert.equal(fixture.focus(), 1);
});

test("Escape is consumed by the open selector so the parent dialog retains its draft", () => {
  const fixture = selectFixture({ options, remote }); let stopped = false;
  fixture.tree.props.onKeyDown({ key: "Escape", preventDefault() {}, stopPropagation: () => { stopped = true; } });
  assert.equal(stopped, true); assert.equal(fixture.focus(), 1);
  assert.ok(fixture.updates.some(([index, value]) => index === 0 && value === false));
});

test("selected label survives an unrelated results page; error replaces empty and retry remains reachable", () => {
  const fixture = selectFixture({ value: "999", options: [], selectedOption: { value: "999", label: "Old selected client" }, remote: { ...remote, error: new Error("offline") } });
  assert.ok(fixture.nodes.some(node => node.props?.children === "Old selected client"));
  assert.ok(fixture.nodes.some(node => node.type === "error-state"));
  assert.ok(!fixture.nodes.some(node => node.props?.children === "common.noResults"));
});
