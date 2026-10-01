import { useMemo } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { dealsApi, type DealListParams } from "../../../api/deals";
import { teamApi } from "../../../api/team";
import { useActiveBusiness } from "../../../hooks/useBusiness";
import { useEntityData } from "../../../hooks/useEntityData";
import { useDebouncedValue } from "../../../hooks/useDebouncedValue";
import type { ActivityEvent, BotConversation, Id, Lead, Task } from "../../../types";
import { useDealBoard } from "./useDealBoard";
import { useAuth } from "../../auth/AuthProvider";
import { hasPermission } from "../../../lib/permissions";
import type { DealFiltersState } from "../types";

export function useDeals(filters?: DealFiltersState, viewMode: "table" | "kanban" = "kanban", page = 1, pageSize = 20) {
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const debouncedSearch = useDebouncedValue(filters?.search || "", 300);
  const entityData = useEntityData({
    clients: true,
    pipelines: true,
    pipelineStages: true,
  });
  const teamMembers = useQuery({
    queryKey: ["team-members", business?.id],
    queryFn: () => teamApi.members(business?.id),
    enabled: hasPermission(user, business?.id, "team"),
    retry: false,
  });

  const defaultPipeline = entityData.pipelines.data?.find((pipeline) => pipeline.is_default) || entityData.pipelines.data?.[0];
  const activePipeline = Number(filters?.pipelineId || defaultPipeline?.id || 0);
  const listParams = useMemo<DealListParams>(() => {
    const params: DealListParams = {
      pipeline: activePipeline || undefined,
      page_size: pageSize,
      page,
      ordering: "-updated_at",
    };
    if (!filters) return params;
    if (filters.stageFilter !== "all") params.stage = filters.stageFilter;
    if (filters.statusFilter !== "all") params.status = filters.statusFilter;
    if (filters.ownerFilter) params.owner = filters.ownerFilter;
    if (debouncedSearch.trim()) params.search = debouncedSearch.trim();
    if (filters.quickFilter !== "all") params.quick = filters.quickFilter;
    if (filters.quickFilter === "mine") params.mine = true;
    if (filters.sourceFilter) params.source = filters.sourceFilter;
    if (filters.minAmount) params.amount_min = filters.minAmount;
    if (filters.maxAmount) params.amount_max = filters.maxAmount;
    if (filters.dateFrom) params.created_from = filters.dateFrom;
    if (filters.dateTo) params.created_to = filters.dateTo;
    return params;
  }, [activePipeline, debouncedSearch, filters, page, pageSize]);

  const deals = useQuery({
    queryKey: ["deals", "paginated", business?.id, listParams],
    queryFn: () => dealsApi.listPaginated(listParams),
    enabled: Boolean(business && activePipeline && viewMode === "table"),
    retry: false,
    placeholderData: keepPreviousData,
  });

  const { board, loadingMore, loadMoreError, loadMore, retryBoard } = useDealBoard(business?.id, listParams, viewMode === "kanban");

  const summary = useQuery({
    queryKey: ["deals", "summary", business?.id, listParams],
    queryFn: () => dealsApi.summary({ ...listParams, mine: undefined }),
    enabled: Boolean(business && activePipeline),
    retry: false,
    placeholderData: keepPreviousData,
  });

  const clientMap = useMemo(() => new Map((entityData.clients.data || []).map((client) => [client.id, client])), [entityData.clients.data]);
  const stageMap = useMemo(() => new Map((entityData.pipelineStages.data || []).map((stage) => [stage.id, stage])), [entityData.pipelineStages.data]);
  const boardDeals = useMemo(() => board.data?.stages.flatMap((stage) => stage.deals) || [], [board.data?.stages]);
  const boardHasMoreByStage = useMemo(() => new Map((board.data?.stages || []).map((stage) => [String(stage.id), stage.has_more])), [board.data?.stages]);
  const displayDeals = viewMode === "kanban" ? boardDeals : deals.data?.results || [];

  const tasksByDeal = useMemo(() => {
    const map = new Map<Id, Task[]>();
    displayDeals.forEach((deal) => {
      if (!deal.next_task_id || !deal.next_task_title) return;
      map.set(deal.id, [
        {
          id: deal.next_task_id,
          business: deal.business,
          title: deal.next_task_title,
          description: "",
          client: deal.client,
          lead: deal.lead,
          deal: deal.id,
          appointment: null,
          conversation: null,
          parent_task: null,
          assignee: deal.owner,
          created_by: null,
          watchers: [],
          due_at: deal.next_task_due_at || null,
          reminder_at: null,
          snoozed_until: null,
          priority: deal.next_task_priority || "normal",
          status: "open",
          completed_at: null,
          completed_by: null,
          created_at: deal.updated_at,
          updated_at: deal.updated_at,
        },
      ]);
    });
    return map;
  }, [displayDeals]);

  const isLoading =
    entityData.clients.isLoading ||
    entityData.pipelines.isLoading ||
    entityData.pipelineStages.isLoading ||
    deals.isLoading ||
    board.isLoading;

  return {
    business,
    queries: entityData,
    teamMembers,
    activePipeline,
    listParams,
    deals,
    board,
    boardHasMoreByStage,
    boardIsFetchingMore: loadingMore,
    boardLoadMoreError: loadMoreError,
    loadMoreBoardDeals: loadMore,
    retryBoard,
    summary,
    data: {
      clients: entityData.clients.data || [],
      leads: [] as Lead[],
      pipelines: entityData.pipelines.data || [],
      stages: entityData.pipelineStages.data || [],
      deals: displayDeals,
      tasks: Array.from(tasksByDeal.values()).flat(),
      activityEvents: [] as ActivityEvent[],
      conversations: [] as BotConversation[],
      teamMembers: teamMembers.data || [],
      clientMap,
      stageMap,
      tasksByDeal,
    },
    isLoading,
  };
}
