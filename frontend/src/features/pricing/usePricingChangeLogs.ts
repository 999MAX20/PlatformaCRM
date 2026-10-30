import { useState } from "react";
import {
  keepPreviousData,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { kaspiPricingApi } from "../../api/pricing";

import { useActiveBusiness } from "../../hooks/useBusiness";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";

export function usePricingChangeLogs(
  business: ReturnType<typeof useActiveBusiness>["business"],
) {
  const queryClient = useQueryClient();
  const [changeSearch, setChangeSearch] = useState("");
  const debouncedChangeSearch = useDebouncedValue(changeSearch, 300);
  const [changeStatus, setChangeStatus] = useState("");
  const changeLogsQuery = useQuery({
    queryKey: [
      "kaspi-price-change-logs",
      business?.id,
      debouncedChangeSearch,
      changeStatus,
    ],
    queryFn: () =>
      kaspiPricingApi.changeLogs.list({
        business: business?.id,
        search: debouncedChangeSearch || undefined,
        status: changeStatus || undefined,
      }),
    enabled: Boolean(business?.id),
    placeholderData: keepPreviousData,
  });
  const changeLogs = changeLogsQuery.data || [];
  return {
    changeSearch,
    setChangeSearch,
    debouncedChangeSearch,
    changeStatus,
    setChangeStatus,
    changeLogsQuery,
    changeLogs,
  };
}
