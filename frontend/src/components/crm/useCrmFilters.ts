import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router";

export type CrmFilterKind = "clients" | "leads" | "deals";
export type CrmFilterValues = Record<string, string>;
export const crmFilterKeys = ["search", "quick", "scope", "statuses", "source", "assignees", "tag", "tag_mode", "segment", "created_from", "created_to", "expected_close_from", "expected_close_to", "amount_min", "amount_max", "attention_reason", "archive", "handoff", "stage", "pipeline"] as const;
export function crmFilterDefaults(kind: CrmFilterKind): CrmFilterValues {
  return { ...Object.fromEntries(crmFilterKeys.map(key => [key, ""])), quick: "all", scope: "all", archive: "active", tag_mode: "any", statuses: kind === "leads" ? "new,contacted,in_progress" : kind === "deals" ? "open" : "" };
}
function normalize(kind: CrmFilterKind, next: CrmFilterValues, patch: CrmFilterValues): CrmFilterValues {
  if (kind === "clients") { next.scope = "all"; next.quick = ["all", "no_reply"].includes(next.quick) ? next.quick : "all"; }
  if (kind === "leads" && !["all", "new", "in_progress", "attention"].includes(next.quick)) next.quick = "all";
  if (kind === "deals" && !["all", "hot", "no_tasks"].includes(next.quick)) next.quick = "all";
  if (patch.quick && patch.quick !== "all" && patch.statuses === undefined && patch.archive === undefined && kind !== "clients") {
    next.statuses = crmFilterDefaults(kind).statuses;
    next.archive = "active";
  }
  if ((patch.statuses !== undefined && patch.statuses !== crmFilterDefaults(kind).statuses) || (patch.archive && patch.archive !== "active")) next.quick = "all";
  if (patch.scope === "mine") next.assignees = "";
  if (patch.assignees) next.scope = "all";
  return next;
}

/** URL is the source of truth, including browser Back/Forward and exact entity returns. */
export function useCrmFilters(kind: CrmFilterKind) {
  const [params, setParams] = useSearchParams();
  const serialized = params.toString();
  const state = useMemo(() => {
    const query = new URLSearchParams(serialized);
    const result = crmFilterDefaults(kind);
    for (const key of crmFilterKeys) if (query.has(key)) result[key] = query.get(key) || "";
    // Keep existing deep links useful while dropping misleading legacy quick labels.
    if (!query.has("quick") && kind === "leads") result.quick = query.get("filter") || "all";
    if (query.get("filter") === "mine" || query.get("quick") === "mine") { result.scope = "mine"; result.quick = "all"; }
    if (query.get("filter") === "unanswered" || query.get("filter") === "hot") { result.assignees = "unassigned"; result.quick = query.get("filter") === "hot" ? "new" : "all"; }
    if (!query.has("statuses") && query.has("status")) result.statuses = query.get("status") || result.statuses;
    if (!query.has("assignees") && query.has("owner")) result.assignees = query.get("owner") || "";
    for (const [oldKey, newKey] of [["from", "created_from"], ["to", "created_to"], ["min", "amount_min"], ["max", "amount_max"]]) if (!query.has(newKey) && query.has(oldKey)) result[newKey] = query.get(oldKey) || "";
    if (kind !== "clients" && (result.statuses !== crmFilterDefaults(kind).statuses || result.archive !== "active")) result.quick = "all";
    return normalize(kind, result, {});
  }, [serialized, kind]);
  const update = useCallback((patch: CrmFilterValues, replace = false) => {
    const defaults = crmFilterDefaults(kind);
    const next = normalize(kind, { ...state, ...patch }, patch);
    setParams(current => {
      const query = new URLSearchParams(current);
      for (const key of ["filter", "status", "owner", "from", "to", "min", "max"]) query.delete(key);
      for (const key of crmFilterKeys) {
        if (next[key] && next[key] !== defaults[key]) query.set(key, next[key]); else query.delete(key);
      }
      query.delete("page");
      return query;
    }, { replace });
  }, [kind, state, setParams]);
  const reset = () => update({ ...crmFilterDefaults(kind), pipeline: state.pipeline });
  const defaults = crmFilterDefaults(kind);
  const hasFilters = crmFilterKeys.some(key => key !== "pipeline" && Boolean(state[key]) && state[key] !== defaults[key]);
  return { state, update, reset, hasFilters };
}

export function crmFilterParams(kind: CrmFilterKind, state: CrmFilterValues) {
  const params: Record<string, string> = { workspace: "true" };
  for (const key of crmFilterKeys) if (state[key]) params[key] = state[key];
  if (kind === "clients") { params.q = state.search; params.quick_filter = state.quick; delete params.quick; }
  if (state.archive !== "active") params.include_archived = "true";
  return params;
}
