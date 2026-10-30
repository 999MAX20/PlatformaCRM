import { infiniteQueryOptions } from "@tanstack/react-query";
import { tasksApi, type TaskListParams } from "../../api/tasks";
import type { Id } from "../../types";

export function taskWorkspaceParams(business: Id, params: URLSearchParams, search = params.get("search") || "") {
  const scope = params.get("tab") || "my";
  const bucket = params.get("bucket") || "active";
  const base: TaskListParams = {
    business, tab: scope === "all" ? undefined : scope, search: search || undefined,
    priority: params.get("priority") || undefined, assignee: params.get("assignee") || undefined,
  };
  const list: TaskListParams = {
    ...base, status: bucket === "done" || bucket === "cancelled" ? bucket : params.get("status") || "active",
    bucket: ["overdue", "today", "noDue"].includes(bucket) ? bucket : undefined,
    ordering: "smart", page_size: 40,
  };
  return { base, list };
}

export function taskWorkspaceQuery(params: TaskListParams) {
  return infiniteQueryOptions({
    queryKey: ["tasks", "workspace", params], initialPageParam: 1,
    queryFn: ({ pageParam }) => tasksApi.listPage({ ...params, page: pageParam }),
    getNextPageParam: (last, pages) => last.next ? pages.length + 1 : undefined,
  });
}
