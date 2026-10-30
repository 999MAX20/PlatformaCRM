import assert from "node:assert/strict";
import fs from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import vm from "node:vm";
import test from "node:test";
import { QueryClient, infiniteQueryOptions, queryOptions } from "@tanstack/react-query";

function setup() {
  const requests = [];
  const stub = name => new Proxy({}, { get: (_, method) => async params => { requests.push({ name, method, params }); return { results: [], next: params?.page === 1 ? "/next" : null }; } });
  const context = { URL, URLSearchParams, Promise, Number, infiniteQueryOptions, queryOptions,
    tasksApi: stub("tasks"), workQueuesApi: stub("queues"), clientsApi: stub("clients"), leadsApi: stub("leads"),
    dealsApi: stub("deals"), pipelinesApi: stub("pipelines"), pipelineStagesApi: stub("stages"),
    notificationsApi: stub("notifications"), botConversationsApi: stub("bots"),
  };
  const source = ["app/routeMetadata.ts", "features/tasks/taskWorkspaceQueries.ts", "features/dashboard/dashboardQueries.ts", "lib/prefetch.ts"]
    .map(file => fs.readFileSync(new URL(`../../src/${file}`, import.meta.url), "utf8").replace(/^import .*;\r?\n/gm, "")).join("\n");
  const api = vm.runInNewContext(stripTypeScriptTypes(source).replaceAll("export function", "function").replaceAll("export const", "const") + "\n({prefetchRouteData,taskWorkspaceQuery,taskWorkspaceParams,workQueuesQuery})", context);
  return { requests, ...api };
}

test("task hover warms the actual infinite workspace contract and supports the next page", async () => {
  const h = setup(), client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
  const pending = [];
  h.prefetchRouteData("/app/tasks?bucket=today&assignee=9", { prefetchInfiniteQuery: options => { const result = client.prefetchInfiniteQuery(options); pending.push(result); return result; } }, "7");
  await Promise.all(pending);
  const options = h.taskWorkspaceQuery(h.taskWorkspaceParams(7, new URLSearchParams("bucket=today&assignee=9")).list);
  const data = client.getQueryData(options.queryKey);
  assert.equal(data.pages.length, 1);
  assert.equal(data.pageParams[0], 1);
  assert.equal(h.requests.length, 1);
  assert.equal(h.requests[0].method, "listPage");
  assert.equal(h.requests[0].params.business, 7);
  assert.equal(h.requests[0].params.bucket, "today");
  const next = options.getNextPageParam(data.pages[0], data.pages);
  await options.queryFn({ pageParam: next });
  assert.equal(h.requests[1].params.page, 2);
  client.clear();
});

test("dashboard prefetch only loads its common queue query, not legacy lists or role-dependent AI", async () => {
  const h = setup(), pending = [];
  h.prefetchRouteData("/app/dashboard", { prefetchQuery: options => { pending.push(options.queryFn()); } }, 7);
  await Promise.all(pending);
  assert.equal(h.requests.length, 1);
  assert.equal(h.requests[0].name, "queues");
  assert.equal(h.requests[0].params.limit, 8);
});

test("lead prefetch does not load the obsolete unpaginated main list", async () => {
  const h = setup(), pending = [];
  h.prefetchRouteData("/app/leads", { prefetchQuery: options => { pending.push(options.queryFn()); } }, 7);
  await Promise.all(pending);
  assert.equal(h.requests.some(r => r.name === "leads"), false);
});

test("missing or invalid Business and the role-dependent /app redirect do not prefetch", () => {
  const h = setup(), client = { prefetchQuery() { assert.fail("unexpected request"); }, prefetchInfiniteQuery() { assert.fail("unexpected request"); } };
  for (const business of [undefined, null, "invalid", -1]) h.prefetchRouteData("/app/tasks", client, business);
  h.prefetchRouteData("/app", client, 7);
});
