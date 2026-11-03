import { useInfiniteQuery } from "@tanstack/react-query";
import { appointmentsApi } from "../api/appointments";
import { useAuth } from "../features/auth/AuthProvider";
import { hasPermission } from "../lib/permissions";
import { useActiveBusiness } from "./useBusiness";
import { useDebouncedValue } from "./useDebouncedValue";

export function useRecordSearch(query: string, enabled = true) {
  const { user } = useAuth();
  const { business } = useActiveBusiness();
  const allowed = !!business && hasPermission(user, business.id, "appointments", "view");
  const term = useDebouncedValue(query.trim(), 300);
  const result = useInfiniteQuery({
    queryKey: ["appointments", "search", business?.id, user?.id, term],
    queryFn: ({ pageParam }) => appointmentsApi.workspace({ business: business!.id, q: term || undefined, page: pageParam, page_size: 20, ordering: "-start_at" }),
    initialPageParam: 1,
    getNextPageParam: (last, pages) => last.next ? pages.length + 1 : undefined,
    enabled: enabled && allowed,
    retry: false,
  });
  const waiting = query.trim() !== term;
  return { ...result, allowed,
    records: enabled && allowed && !waiting && !result.isError ? result.data?.pages.flatMap(page => page.results) ?? [] : [],
    loading: enabled && allowed && (waiting || result.isPending),
  };
}
