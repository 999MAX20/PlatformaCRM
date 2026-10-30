import { useMemo, useState } from "react";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { kaspiPricingApi, type PricingCatalogItem } from "../../api/pricing";

import { useActiveBusiness } from "../../hooks/useBusiness";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";

import type { usePricingRules } from "./usePricingRules";

export function usePricingCatalog(
  business: ReturnType<typeof useActiveBusiness>["business"],
  form: ReturnType<typeof usePricingRules>["form"],
) {
  const queryClient = useQueryClient();
  const [catalogMinPrices, setCatalogMinPrices] = useState<
    Record<string, string>
  >({});
  const [selectedCatalogIds, setSelectedCatalogIds] = useState<Array<string>>(
    [],
  );
  const [bulkMinPrice, setBulkMinPrice] = useState("");
  const [bulkStepAmount, setBulkStepAmount] = useState("1");
  const [bulkMaxChanges, setBulkMaxChanges] = useState("3");
  const [catalogSearch, setCatalogSearch] = useState("");
  const debouncedCatalogSearch = useDebouncedValue(catalogSearch, 300);
  const [catalogSource, setCatalogSource] = useState("");
  const [catalogRuleState, setCatalogRuleState] = useState("");
  const catalogQuery = useQuery({
    queryKey: [
      "kaspi-pricing-catalog",
      business?.id,
      debouncedCatalogSearch,
      catalogSource,
      catalogRuleState,
    ],
    queryFn: () =>
      kaspiPricingApi.catalog.list({
        business: business?.id,
        search: debouncedCatalogSearch || undefined,
        source: catalogSource || undefined,
        rule_state: catalogRuleState || undefined,
      }),
    enabled: Boolean(business?.id),
    placeholderData: keepPreviousData,
  });
  const syncCatalog = useMutation({
    mutationFn: () => {
      if (!business?.id) throw new Error("Business is required.");
      return kaspiPricingApi.catalog.sync({ business: business.id });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kaspi-pricing-catalog"] });
    },
  });
  const createRuleFromCatalog = useMutation({
    mutationFn: (item: PricingCatalogItem) =>
      kaspiPricingApi.catalog.createRule({
        id: item.id,
        minPrice: catalogMinPrices[String(item.id)] || "",
        currentPrice: item.current_price || undefined,
        stepAmount: form.step_amount || "1",
        mode: "approval",
        maxChangesPerDay: Number(form.max_changes_per_day || 3),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kaspi-pricing-catalog"] });
      queryClient.invalidateQueries({ queryKey: ["kaspi-pricing-rules"] });
    },
  });
  const bulkCreateRules = useMutation({
    mutationFn: () =>
      kaspiPricingApi.catalog.bulkCreateRules({
        itemIds: selectedCatalogIds.map((id) => Number(id)),
        minPrice: bulkMinPrice,
        stepAmount: bulkStepAmount || "1",
        mode: "approval",
        maxChangesPerDay: Number(bulkMaxChanges || 3),
      }),
    onSuccess: () => {
      setSelectedCatalogIds([]);
      queryClient.invalidateQueries({ queryKey: ["kaspi-pricing-catalog"] });
      queryClient.invalidateQueries({ queryKey: ["kaspi-pricing-rules"] });
    },
  });
  const catalogItems = catalogQuery.data || [];
  const catalogSources = useMemo(
    () =>
      Array.from(
        new Set(catalogItems.map((item) => item.source).filter(Boolean)),
      ).sort(),
    [catalogItems],
  );
  return {
    catalogMinPrices,
    setCatalogMinPrices,
    selectedCatalogIds,
    setSelectedCatalogIds,
    bulkMinPrice,
    setBulkMinPrice,
    bulkStepAmount,
    setBulkStepAmount,
    bulkMaxChanges,
    setBulkMaxChanges,
    catalogSearch,
    setCatalogSearch,
    debouncedCatalogSearch,
    catalogSource,
    setCatalogSource,
    catalogRuleState,
    setCatalogRuleState,
    catalogQuery,
    syncCatalog,
    createRuleFromCatalog,
    bulkCreateRules,
    catalogItems,
    catalogSources,
  };
}
