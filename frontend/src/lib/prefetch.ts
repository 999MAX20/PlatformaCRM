import { routeMetadata } from "../app/routeMetadata";
import type { QueryClient } from "@tanstack/react-query";

import { botConversationsApi } from "../api/bots";
import { clientsApi } from "../api/clients";
import { dealsApi, pipelineStagesApi, pipelinesApi } from "../api/deals";
import { leadsApi } from "../api/leads";
import { notificationsApi } from "../api/notifications";
import { tasksApi } from "../api/tasks";
import { inboxApi, inboxQueryKeys, normalizeFilters } from "../api/inbox";
import { taskWorkspaceParams, taskWorkspaceQuery } from "../features/tasks/taskWorkspaceQueries";
import { workQueuesQuery } from "../features/dashboard/dashboardQueries";

const prefetchOptions = {
  staleTime: 5 * 60_000,
};

export function prefetchRouteData(path: string, queryClient: QueryClient, businessId?: number | null | string) {
  if (!businessId) return;
  const business = Number(businessId);
  if (!Number.isSafeInteger(business) || business <= 0) return;
  const url = new URL(path, "http://local.invalid");
  path = url.pathname;
  if (path === routeMetadata.dashboard.path) {
    // Role-dependent metrics/AI remain owned by the dashboard's permission guards.
    void queryClient.prefetchQuery(workQueuesQuery(business));
    return;
  }

  if (path.startsWith(routeMetadata.leads.path)) {
    void Promise.allSettled([
      queryClient.prefetchQuery({ queryKey: ["clients"], queryFn: clientsApi.list, ...prefetchOptions }),
      queryClient.prefetchQuery({ queryKey: ["tasks"], queryFn: tasksApi.list, ...prefetchOptions }),
    ]);
    return;
  }

  if (path.startsWith(routeMetadata.clients.path)) {
    void Promise.allSettled([
      queryClient.prefetchQuery({ queryKey: ["clients"], queryFn: clientsApi.list, ...prefetchOptions }),
      queryClient.prefetchQuery({ queryKey: ["leads"], queryFn: leadsApi.list, ...prefetchOptions }),
      queryClient.prefetchQuery({ queryKey: ["deals"], queryFn: dealsApi.list, ...prefetchOptions }),
    ]);
    return;
  }

  if (path.startsWith(routeMetadata.deals.path)) {
    void Promise.allSettled([
      queryClient.prefetchQuery({ queryKey: ["deals"], queryFn: dealsApi.list, ...prefetchOptions }),
      queryClient.prefetchQuery({ queryKey: ["pipelines"], queryFn: pipelinesApi.list, ...prefetchOptions }),
      queryClient.prefetchQuery({ queryKey: ["pipeline-stages"], queryFn: pipelineStagesApi.list, ...prefetchOptions }),
      queryClient.prefetchQuery({ queryKey: ["clients"], queryFn: clientsApi.list, ...prefetchOptions }),
    ]);
    return;
  }

  if (path.startsWith(routeMetadata.conversations.path)) {
    const summaryKey = ["inbox-summary", businessId];
    const conversationFilters = normalizeFilters({});
    void Promise.allSettled([
      queryClient.prefetchQuery({ queryKey: inboxQueryKeys.conversations(conversationFilters), queryFn: () => inboxApi.listConversations(conversationFilters), ...prefetchOptions }),
      queryClient.prefetchQuery({ queryKey: summaryKey, queryFn: inboxApi.getSummary, ...prefetchOptions }),
    ]);
    return;
  }

  if (path === routeMetadata.tasks.path) {
    void queryClient.prefetchInfiniteQuery(taskWorkspaceQuery(taskWorkspaceParams(business, url.searchParams).list));
    return;
  }

  if (path.startsWith(routeMetadata.aiAgents.path)) {
    void queryClient.prefetchQuery({ queryKey: ["bot-conversations"], queryFn: botConversationsApi.list, ...prefetchOptions });
    return;
  }

  if (path.startsWith(routeMetadata.settings.path)) {
    void queryClient.prefetchQuery({ queryKey: ["notifications"], queryFn: notificationsApi.list, ...prefetchOptions });
  }
}
