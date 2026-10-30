import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { automationRunsApi } from "../../api/automations";

import type { AutomationRun, Id } from "../../types";

type HistoryFilters = { page: number; pageSize: number; status: string; triggerType: string };
const defaults: HistoryFilters = { page: 1, pageSize: 20, status: "", triggerType: "" };

export function useAutomationRuns(businessId?: Id, userId?: Id) {
  const queryClient = useQueryClient();
  const scope = `${businessId}:${userId}`;
  const [state, setState] = useState({ scope, ...defaults });
  const filters = state.scope === scope ? state : defaults;
  const [selection, setSelection] = useState<{ scope: string; run: AutomationRun | null }>({ scope, run: null });
  const setSelectedRun = (run: AutomationRun | null) => setSelection({ scope, run });
  const updateFilters = (patch: Partial<HistoryFilters>) => {
    setState({ scope, ...filters, page: 1, ...patch });
    setSelectedRun(null);
  };
  const runs = useQuery({
    queryKey: ["automation-runs", businessId, userId, filters.status, filters.triggerType, filters.page, filters.pageSize],
    queryFn: () => automationRunsApi.listPage({
      business: businessId!, page: filters.page, page_size: filters.pageSize,
      status: filters.status || undefined, trigger_type: filters.triggerType || undefined,
    }),
    enabled: Boolean(businessId && userId),
    retry: false,
  });
  const selectedRun = selection.scope === scope && !runs.isError ? selection.run : null;
  const onRunChanged = (run: AutomationRun) => {
    void queryClient.invalidateQueries({ queryKey: ["automation-runs"] });
    setSelection(previous => previous.scope === scope && previous.run?.id === run.id ? { scope, run } : previous);
  };
  const retryRunMutation = useMutation({
    mutationFn: (runId: number) => automationRunsApi.retry(runId),
    onSuccess: onRunChanged,
  });
  const cancelRunMutation = useMutation({
    mutationFn: (runId: number) => automationRunsApi.cancel(runId),
    onSuccess: onRunChanged,
  });
  return {
    runs,
    filters,
    updateFilters,
    selectedRun,
    setSelectedRun,
    retryRunMutation,
    cancelRunMutation,
  };
}
