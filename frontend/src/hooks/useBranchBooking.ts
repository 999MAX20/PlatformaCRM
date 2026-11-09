import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { branchesApi } from "../api/branches";
import type { Id } from "../types";

export function useBranchBooking(businessId: Id, initial?: Id | null) {
  const [selection, setSelection] = useState({ businessId, value: initial ? String(initial) : "" });
  const query = useQuery({ queryKey: ["branches", businessId], queryFn: () => branchesApi.listAll({ business: businessId }), enabled: !!businessId });
  const branches = query.data || [];
  const available = branches.filter((branch) => branch.can_book && branch.is_active && !branch.archived_at);
  const enabled = branches.length > 0;
  const requested = selection.businessId === businessId ? selection.value : initial ? String(initial) : "";
  const branchId = enabled ? requested || (available.length === 1 ? String(available[0].id) : "") : "";
  const validSelection = available.some(branch => String(branch.id) === branchId);
  const setBranchId = (value: string) => setSelection({ businessId, value });
  const requiresSelection = available.length > 1 || (!!branchId && !validSelection && available.length > 0);
  const catalog = useQuery({ queryKey: ["branch-catalog", Number(branchId)], queryFn: () => branchesApi.catalog(Number(branchId)), enabled: enabled && validSelection });
  return { branchId, setBranchId, branches: available, enabled, requiresSelection, catalog: catalog.data,
    loading: query.isLoading || catalog.isLoading, error: query.error || catalog.error,
    retry: () => { void query.refetch(); if (validSelection) void catalog.refetch(); },
    ready: !query.isLoading && !query.error && (!enabled || (validSelection && !!catalog.data && !catalog.error)) };
}
