import { useInfiniteQuery } from "@tanstack/react-query";
import { clientsApi } from "../api/clients";
import { useAuth } from "../features/auth/AuthProvider";
import { hasPermission } from "../lib/permissions";
import { useActiveBusiness } from "./useBusiness";
import { useDebouncedValue } from "./useDebouncedValue";

export function useClientSearch(query: string, enabled = true, requestedBusinessId?: number) {
  const { user } = useAuth();
  const { business } = useActiveBusiness();
  const businessId = requestedBusinessId ?? business?.id;
  const allowed = Boolean(businessId && hasPermission(user, businessId, "clients", "view"));
  const term = useDebouncedValue(query.trim(), 300);
  const result = useInfiniteQuery({
    queryKey: ["clients", "search", businessId, user?.id, term],
    queryFn: ({ pageParam }) => clientsApi.listFiltered({ business: businessId, q: term || undefined, page: pageParam, page_size: 20, ordering: "-created_at" }),
    initialPageParam: 1,
    getNextPageParam: (last, pages) => last.next ? pages.length + 1 : undefined,
    enabled: enabled && allowed,
    retry: false,
  });
  const waiting = query.trim() !== term;
  return { ...result, businessId, userId: user?.id, allowed,
    clients: allowed && !waiting && !result.isError ? result.data?.pages.flatMap(page => page.clients) ?? [] : [],
    loading: enabled && allowed && (waiting || result.isPending),
  };
}
