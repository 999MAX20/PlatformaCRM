import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { automationRunsApi } from "../../api/automations";

import type { AutomationRun } from "../../types";

export function useAutomationRuns() {
  const queryClient = useQueryClient();
  const runs = useQuery({
    queryKey: ["automation-runs"],
    queryFn: automationRunsApi.list,
  });
  const [selectedRun, setSelectedRun] = useState<AutomationRun | null>(null);
  const retryRunMutation = useMutation({
    mutationFn: (runId: number) => automationRunsApi.retry(runId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["automation-runs"] }),
  });
  const cancelRunMutation = useMutation({
    mutationFn: (runId: number) => automationRunsApi.cancel(runId),
    onSuccess: (run) => {
      queryClient.invalidateQueries({ queryKey: ["automation-runs"] });
      setSelectedRun(run);
    },
  });
  return {
    runs,
    selectedRun,
    setSelectedRun,
    retryRunMutation,
    cancelRunMutation,
  };
}
