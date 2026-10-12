import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { branchesApi } from "../api/branches";
import type { Id } from "../types";

export function useBranchBooking(businessId: Id, initial?: Id | null) {
  const [branchId, setBranchId] = useState(initial ? String(initial) : "");
  const query = useQuery({ queryKey: ["branches", businessId], queryFn: () => branchesApi.listAll({ business: businessId }), enabled: !!businessId });
  const branches = query.data || [];
  const available = branches.filter((branch) => branch.can_book && branch.is_active && !branch.archived_at);
  const enabled = branches.length > 0;
  useEffect(() => {
    if (!initial && !branchId && available.length === 1) setBranchId(String(available[0].id));
  }, [initial, branchId, available]);
  const catalog = useQuery({ queryKey: ["branch-catalog", Number(branchId)], queryFn: () => branchesApi.catalog(Number(branchId)), enabled: enabled && !!branchId });
  return { branchId, setBranchId, branches: available, enabled, catalog: catalog.data,
    loading: query.isLoading || catalog.isLoading, error: query.error || catalog.error,
    ready: !query.isLoading && !query.error && (!enabled || (!!branchId && !!catalog.data && !catalog.error)) };
}
