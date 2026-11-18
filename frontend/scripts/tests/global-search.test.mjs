import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import vm from "node:vm";
import ts from "typescript";

function render({ query = "needle", open = true, clients = [], records = [], tasks = [], conversations = [], clientState = {} } = {}) {
  const source = fs.readFileSync(new URL("../../src/components/layout/GlobalSearch.tsx", import.meta.url), "utf8");
  const compiled = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  const calls = [], updates = [], listeners = {};
  let state = 0;
  const jsx = (type, props) => ({ type, props });
  const imports = {
    "react/jsx-runtime": { jsx, jsxs: jsx },
    "react": { useMemo: fn => fn(), useRef: () => ({ current: null }), useEffect: fn => fn(),
      useState: () => { const index = state++; return [[open, false, query][index], value => updates.push([index, value])]; } },
    // No location/search-param API: the global control must not read or mutate page filters.
    "react-router": { Link: "a" },
    "lucide-react": Object.fromEntries(["CalendarCheck", "ListChecks", "MessageCircle", "Search", "User", "X"].map(key => [key, "svg"])),
    "../../lib/format": { formatDateTime: value => value },
    "../../lib/cn": { cn: (...values) => values.filter(Boolean).join(" ") },
    "../../lib/i18n": { useI18n: () => ({ t: key => key, language: "ru" }) },
    "../ui/Button": { Button: "button" }, "../ui/StateViews": { ErrorState: "error" },
    "../../hooks/useEntityData": { useEntityData: options => { calls.push(["entities", options]); return { services: { data: [] }, tasks: { data: tasks }, botConversations: { data: conversations } }; } },
    "../../hooks/useClientSearch": { useClientSearch: (...args) => { calls.push(["clients", ...args]); return { clients, ...clientState }; } },
    "../../hooks/useRecordSearch": { useRecordSearch: (...args) => { calls.push(["records", ...args]); return { records }; } },
  };
  const exports = {};
  vm.runInNewContext(compiled, { exports, require: name => { assert.ok(name in imports, name); return imports[name]; },
    document: { addEventListener: (name, fn) => { listeners[name] = fn; } },
    window: { addEventListener: (name, fn) => { listeners[name] = fn; }, setTimeout: fn => fn() },
  });
  const tree = exports.GlobalSearch();
  function flatten(node) {
    if (!node || typeof node !== "object") return [];
    if (Array.isArray(node)) return node.flatMap(flatten);
    return [node, ...flatten(node.props?.children)];
  }
  return { nodes: flatten(tree), calls, updates, listeners };
}

test("global search has one fixed scope, opens both remote searches and never needs page URL hooks", () => {
  const result = render();
  assert.deepEqual(result.calls.slice(1), [["records", "needle", true], ["clients", "needle", true]]);
  assert.equal(result.nodes.find(node => node.type === "input").props.placeholder, "search.placeholder.global");
  assert.ok(!result.nodes.some(node => ["search.scopePage", "search.scopeGlobal"].includes(node.props?.children)));
  result.nodes.find(node => node.type === "input").props.onChange({ target: { value: "new query" } });
  assert.deepEqual(result.updates, [[2, "new query"], [0, true]]);
});

test("result categories retain entity destinations and clicking closes the dropdown", () => {
  const result = render({ clients: [{ id: 1, full_name: "needle" }], records: [{ id: 2, client_name: "needle", status: "created" }],
    tasks: [{ id: 3, title: "needle" }], conversations: [{ id: 4, client_name: "needle" }] });
  const links = result.nodes.filter(node => node.type === "a");
  assert.deepEqual(links.map(node => node.props.to), ["/app/clients?client=1", "/app/appointments/2", "/app/conversations?conversation=4", "/app/tasks?task=3"]);
  links[0].props.onClick();
  assert.deepEqual(result.updates, [[0, false], [1, false]]);
});

test("client failures show retry instead of an empty result; Escape closes the global control", () => {
  let retries = 0;
  const result = render({ clientState: { error: new Error("offline"), refetch: () => retries++ } });
  assert.ok(!result.nodes.some(node => node.props?.children === "search.empty"));
  result.nodes.find(node => node.type === "error").props.action.props.onClick();
  assert.equal(retries, 1);
  result.listeners.keydown({ key: "Escape" });
  assert.deepEqual(result.updates, [[0, false], [1, false]]);
});
