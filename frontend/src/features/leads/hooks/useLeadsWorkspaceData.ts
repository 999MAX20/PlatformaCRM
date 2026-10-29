import { useCrmFilters, crmFilterParams } from "../../../components/crm/useCrmFilters";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { getApiErrorMessage } from "../../../api/client";
import { normalizeAppError } from "../../../api/appError";
import { leadsApi } from "../../../api/leads";
import { teamApi } from "../../../api/team";
import { useActiveBusiness } from "../../../hooks/useBusiness";
import { useEntityData } from "../../../hooks/useEntityData";
import { useDebouncedValue } from "../../../hooks/useDebouncedValue";
import { hasPermission } from "../../../lib/permissions";
import { leadOfflineScope } from "../../../lib/leadOfflineStorage";
import { useAuth } from "../../auth/AuthProvider";
import type { Id } from "../../../types";
import type { LeadAiInsight, LeadFilter, Translate } from "../types";
import { leadAiInsight } from "../utils/leadFormat";
import { useLeadOfflineQueue } from "./useLeadOfflineQueue";
import { useLeadRealtime } from "./useLeadRealtime";
import { useLeadSelectionContext } from "./useLeadSelectionContext";
import { useLeadsWorkspaceDisplay } from "./useLeadsWorkspaceDisplay";

export function useLeadsWorkspaceData({
  search,
  sortByAi,
  page,
  pageSize,
  selectedId,
  t,
  setNotice,
  showWarning,
}: {
  filter: LeadFilter;
  source: string;
  search: string;
  sortByAi: boolean;
  page: number;
  pageSize: number;
  selectedId: Id | null;
  t: Translate;
  setNotice: (message: string | null, tone?: "success" | "info" | "warning" | "danger") => void;
  showWarning: (message: string) => void;
}) {
  const { business } = useActiveBusiness();
  const { state } = useCrmFilters("leads");
  const { user } = useAuth();
  const debouncedSearch = useDebouncedValue(search, 300);
  const { clients, services, resources, tasks, deals, appointments, botConversations } = useEntityData({
    clients: true,
    services: true,
    resources: true,
    tasks: true,
    deals: true,
    appointments: true,
    botConversations: true,
  });

  const teamMembers = useQuery({
    queryKey: ["team-members", business?.id],
    queryFn: () => teamApi.members(business?.id),
    enabled: hasPermission(user, business?.id, "team"),
    retry: false,
  });
  const leadListParams = useMemo(() => ({
    ...crmFilterParams("leads", { ...state, search: debouncedSearch.trim() }),
    page, page_size: pageSize, ordering: sortByAi ? "-updated_at" : "-created_at",
  }), [state, debouncedSearch, page, pageSize, sortByAi]);

  const leads = useQuery({
    queryKey: ["leads", "paginated", user?.id, business?.id, leadListParams],
    queryFn: () => leadsApi.listPaginated(leadListParams),
    enabled: Boolean(business),
    retry: false,
    placeholderData: (previous, query) => query && query.queryKey[2] === user?.id && query.queryKey[3] === business?.id ? previous : undefined,
  });
  const leadSummary = useQuery({
    queryKey: ["leads", "summary", business?.id, leadListParams],
    queryFn: () => leadsApi.summary(leadListParams),
    enabled: Boolean(business),
    retry: false,
  });

  const errorCategory = leads.error ? normalizeAppError(leads.error).category : undefined;
  const accessDenied = errorCategory === "authentication" || errorCategory === "permission";
  const onlineLeads = useMemo(() => accessDenied ? [] : leads.data?.results || [], [accessDenied, leads.data]);
  const offlineScope = useMemo(() => leadOfflineScope(user, business?.id), [user, business?.id]);
  const { isOnline, offlineQueue, cachedLeads, enqueueOfflineAction, recoverOfflineAction, storageError, syncing } = useLeadOfflineQueue({
    scope: offlineScope,
    onlineLeads,
    hasFreshData: leads.isSuccess && !leads.isPlaceholderData,
    accessDenied,
    t,
    onNotice: setNotice,
    onWarning: showWarning,
  });
  const allLeads = onlineLeads.length ? onlineLeads : (!isOnline ? cachedLeads : []);
  const workspaceErrors = [clients.error, services.error, leads.error, leadSummary.error];
  const pageError = workspaceErrors.find(Boolean);
  // A usable offline snapshot is the fallback for connectivity/server failures,
  // never for revoked access or an invalid request. The offline notice stays visible.
  const usingOfflineCache = !isOnline && cachedLeads.length > 0 && workspaceErrors.every(error =>
    !error || ["offline", "temporary", "provider"].includes(normalizeAppError(error).category));
  useLeadRealtime({
    businessReady: Boolean(business),
    isOnline,
    leadsQuery: leads,
    queryScope: JSON.stringify([business?.id, user?.id, leadListParams]),
    t,
    onNotice: setNotice,
  });

  const clientList = clients.data || [];
  const serviceList = services.data || [];
  const taskList = tasks.data || [];
  const dealList = deals.data || [];
  const appointmentList = appointments.data || [];
  const conversationList = botConversations.data || [];
  const resourceList = resources.data || [];
  const teamList = Array.isArray(teamMembers.data) ? teamMembers.data : [];
  const aiInsights = useMemo(() => {
    const result = new Map<Id, LeadAiInsight>();
    allLeads.forEach((lead) => {
      const insight = leadAiInsight(lead, clientList, serviceList, allLeads, t);
      result.set(lead.id, {
        ...insight,
        score: typeof lead.ai_score === "number" ? lead.ai_score : insight.score,
        lossRisk: typeof lead.loss_risk === "number" ? lead.loss_risk : insight.lossRisk,
        recommendation: lead.recommended_action || insight.recommendation,
      });
    });
    return result;
  }, [allLeads, clientList, serviceList, t]);

  const rows = useMemo(() => allLeads, [allLeads]);
  const totalLeadCount = leads.data?.count ?? rows.length;
  const pageCount = Math.max(1, Math.ceil(totalLeadCount / pageSize));
  const safePage = Math.min(page, pageCount);
  const pageRows = rows;
  const selectedContext = useLeadSelectionContext({
    businessId: business?.id,
    rows,
    selectedId,
    clients: clientList,
    services: serviceList,
    tasks: taskList,
    deals: dealList,
    appointments: appointmentList,
    conversations: conversationList,
    aiInsights,
    t,
  });
  const display = useLeadsWorkspaceDisplay({
    t,
    leadSummary: leadSummary.isError ? undefined : leadSummary.data,
    totalLeadCount,
    allLeads,
    aiInsights,
    userId: user?.id,
    pageRows,
    safePage,
    pageSize,
    pageCount,
  });

  return {
    business,
    clients,
    services,
    resources,
    tasks,
    leads,
    retryWorkspace: () => { void Promise.all([clients.refetch(), services.refetch(), leads.refetch(), leadSummary.refetch()]); },
    pageError: usingOfflineCache ? undefined : pageError,
    pageErrorMessage: getApiErrorMessage(pageError),
    isPageLoading: leads.isLoading || clients.isLoading || services.isLoading || tasks.isLoading,
    allLeads,
    rows,
    pageRows,
    totalLeadCount,
    pageCount,
    safePage,
    offlineQueue,
    enqueueOfflineAction,
    recoverOfflineAction, storageError, syncing, isOnline,
    clientList,
    serviceList,
    resourceList,
    teamList,
    aiInsights,
    ...selectedContext,
    ...display,
  };
}
