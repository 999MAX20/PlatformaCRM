import { useCallback, useMemo } from "react";
import { useCrmFilters, crmFilterDefaults } from "../../../components/crm/useCrmFilters";
import type { DealFiltersState, DealQuickFilter, DealStatusFilter } from "../types";

const fields: Record<string, string> = { pipelineId: "pipeline", stageFilter: "stage", statusFilter: "statuses", ownerFilter: "assignees", search: "search", quickFilter: "quick", sourceFilter: "source", minAmount: "amount_min", maxAmount: "amount_max", dateFrom: "created_from", dateTo: "created_to" };
export function useDealFilters() {
  const { state, update, reset } = useCrmFilters("deals");
  const filters = useMemo<DealFiltersState>(() => ({
    pipelineId: state.pipeline, stageFilter: state.stage || "all", statusFilter: state.statuses as DealStatusFilter,
    ownerFilter: state.assignees, search: state.search, quickFilter: state.quick as DealQuickFilter,
    sourceFilter: state.source, minAmount: state.amount_min, maxAmount: state.amount_max,
    dateFrom: state.created_from, dateTo: state.created_to, expanded: false,
  }), [state]);
  const updateFilters = useCallback((patch: Partial<DealFiltersState>) => {
    update(Object.fromEntries(Object.entries(patch).filter(([key]) => fields[key]).map(([key, value]) => [fields[key], key === "stageFilter" && value === "all" ? "" : String(value)])));
  }, [update]);
  const defaults = crmFilterDefaults("deals");
  const activeFilterCount = Object.keys(state).filter(key => key !== "pipeline" && state[key] && state[key] !== defaults[key]).length;
  return { filters, updateFilters, resetFilters: reset, activeFilterCount };
}
