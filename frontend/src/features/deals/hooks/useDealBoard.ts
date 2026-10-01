import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { dealsApi, type DealListParams } from "../../../api/deals";
import type { DealBoard } from "../../../types";

const STAGE_PAGE_SIZE = 25;

export function useDealBoard(businessId: number | undefined, params: DealListParams, enabled: boolean) {
  const queryClient = useQueryClient();
  const boardParams = { ...params, page: undefined, page_size: undefined };
  const queryKey = ["deals", "board", businessId, boardParams] as const;
  const board = useQuery({
    queryKey,
    queryFn: () => dealsApi.board({ ...boardParams, limit_per_stage: STAGE_PAGE_SIZE }),
    enabled: enabled && Boolean(businessId && params.pipeline),
    retry: false,
    placeholderData: keepPreviousData,
  });
  const more = useMutation({
    mutationFn: async (input: { stageId: string; offset: number; params: DealListParams; queryKey: readonly unknown[] }) => ({
      ...input,
      result: await dealsApi.board({ ...input.params, stage: input.stageId, offset: input.offset, limit_per_stage: STAGE_PAGE_SIZE }),
    }),
    onSuccess: ({ result, stageId, queryKey: loadedKey }) => {
      const loaded = result.stages.find((stage) => String(stage.id) === stageId);
      if (!loaded) return;
      // A filter/account change must never append old results to the active board.
      queryClient.setQueryData<DealBoard>(loadedKey, (current) => current ? {
        ...current,
        stages: current.stages.map((stage) => String(stage.id) === stageId ? {
          ...loaded,
          offset: 0,
          deals: Array.from(new Map([...stage.deals, ...loaded.deals].map((deal) => [deal.id, deal])).values()),
        } : stage),
      } : current);
    },
  });

  return {
    board,
    loadingMore: more.isPending,
    loadMoreError: more.error,
    loadMore: (stageId: string) => {
      const stage = board.data?.stages.find((item) => String(item.id) === stageId);
      if (!stage?.has_more || more.isPending || board.isPlaceholderData) return;
      more.mutate({ stageId, offset: stage.deals.length, params: boardParams, queryKey });
    },
    retryBoard: () => { more.reset(); void board.refetch(); },
  };
}
