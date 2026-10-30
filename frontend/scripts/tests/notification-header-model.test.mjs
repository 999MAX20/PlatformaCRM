import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const sourceRoot = fileURLToPath(new URL("../../src/", import.meta.url));

function model() {
  const requests = [],
    invalidations = [],
    queries = [],
    mutations = [],
    effects = [];
  const listeners = new Map(),
    states = [];
  const queryClient = {
    invalidateQueries: (options) => {
      invalidations.push(options.queryKey);
      return Promise.resolve();
    },
  };
  const api = new Proxy(
    {},
    {
      get:
        (_, method) =>
        async (...args) => {
          requests.push({ method, args });
          return [];
        },
    },
  );
  function load(file) {
    const exports = {};
    const source = fs.readFileSync(file, "utf8");
    const compiled = ts.transpileModule(source, {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        target: ts.ScriptTarget.ES2022,
      },
    }).outputText;
    vm.runInNewContext(compiled, {
      exports,
      document: {
        addEventListener: (name, handler) => listeners.set(name, handler),
        removeEventListener: (name) => listeners.delete(name),
      },
      require: (name) => {
        if (name === "react")
          return {
            useRef: (value) => ({ current: value }),
            useEffect: (effect) => effects.push(effect),
          };
        if (name === "@tanstack/react-query")
          return {
            useQueryClient: () => queryClient,
            useQuery: (options) => {
              queries.push(options);
              return {
                data:
                  options.queryKey[0] === "notifications" ? [] : { unread: 2 },
              };
            },
            useMutation: (options) => {
              mutations.push(options);
              return {};
            },
          };
        if (name.endsWith("/api/notifications"))
          return { notificationsApi: api };
        if (name.endsWith("/lib/realtime"))
          return {
            realtimeIntervals: { notificationsMs: 30000 },
            realtimeQueryOptions: {},
          };
        if (name.startsWith("."))
          return load(path.resolve(path.dirname(file), name + ".ts"));
        throw new Error(`Unexpected runtime dependency: ${name}`);
      },
    });
    return exports;
  }
  const { useNotificationBell } = load(
    path.join(sourceRoot, "components/layout/useNotificationBell.ts"),
  );
  const render = (open) =>
    useNotificationBell({
      user: { id: 5 },
      business: { id: 8 },
      t: (key) => key,
      showNotifications: open,
      setShowNotifications: (value) => states.push(value),
    });
  return {
    render,
    requests,
    invalidations,
    queries,
    mutations,
    effects,
    listeners,
    states,
  };
}

test("closed bell does not fetch the list; opening requests the active business", async () => {
  const closed = model();
  closed.render(false);
  assert.equal(
    closed.queries.find((q) => q.queryKey[0] === "notifications").enabled,
    false,
  );
  const open = model();
  open.render(true);
  const list = open.queries.find((q) => q.queryKey[0] === "notifications");
  assert.equal(list.enabled, true);
  await list.queryFn();
  assert.equal(open.requests[0].method, "list");
  assert.equal(open.requests[0].args[0].business, 8);
  assert.equal(open.requests[0].args[0].surface, "bell");
});

test("read and read-all invalidate both list and unread summary", async () => {
  const h = model();
  h.render(true);
  await h.mutations[0].mutationFn(11);
  await h.mutations[0].onSuccess();
  await h.mutations[1].mutationFn();
  await h.mutations[1].onSuccess();
  assert.ok(
    h.requests.some((r) => r.method === "markRead" && r.args[0] === 11),
  );
  assert.ok(
    h.requests.some(
      (r) => r.method === "markAllRead" && r.args[0].surface === "bell",
    ),
  );
  assert.equal(
    h.invalidations.filter((key) => key[0] === "notifications").length,
    2,
  );
  assert.equal(
    h.invalidations.filter((key) => key[0] === "notifications-summary").length,
    2,
  );
});

test("Escape and outside click close the bell and listeners are removed", () => {
  const h = model();
  h.render(true);
  const cleanup = h.effects.map((effect) => effect());
  h.listeners.get("keydown")({ key: "Escape" });
  h.listeners.get("pointerdown")({ target: {} });
  assert.deepEqual(h.states, [false, false]);
  cleanup.forEach((fn) => fn?.());
  assert.equal(h.listeners.size, 0);
});

test("legacy notification links preserve their query when mapped", () => {
  const h = model(),
    bell = h.render(false);
  assert.equal(
    bell.resolveNotificationRoute("/tasks?status=open"),
    "/app/tasks?status=open",
  );
  assert.equal(
    bell.resolveNotificationRoute("/app/clients/7"),
    "/app/clients/7",
  );
});
