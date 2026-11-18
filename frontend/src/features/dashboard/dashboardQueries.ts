import { queryOptions } from "@tanstack/react-query";
import { workQueuesApi } from "../../api/workQueues";
import type { Id } from "../../types";

export function workQueuesQuery(business: Id | undefined, limit = 8) {
  return queryOptions({
    queryKey: ["work-queues", business, limit, "appointments"],
    queryFn: () => workQueuesApi.get({ business: business!, limit, workflow: "appointments" }),
    enabled: Boolean(business),
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
    refetchOnMount: "always",
  });
}
