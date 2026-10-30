import { queryOptions } from "@tanstack/react-query";
import { workQueuesApi } from "../../api/workQueues";
import type { Id } from "../../types";

export function workQueuesQuery(business: Id | undefined, limit = 8) {
  return queryOptions({
    queryKey: ["work-queues", business, limit],
    queryFn: () => workQueuesApi.get({ business: business!, limit }),
    enabled: Boolean(business),
  });
}
