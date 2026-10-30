import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  kaspiPricingApi,
  type KaspiCompetitorOffer,
  type KaspiPricingRecommendation,
  type KaspiPricingRule,
} from "../../api/pricing";

import { useActiveBusiness } from "../../hooks/useBusiness";

export function usePricingRules(
  business: ReturnType<typeof useActiveBusiness>["business"],
) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    product_sku: "",
    product_name: "",
    current_price: "",
    min_price: "",
    step_amount: "1",
    mode: "approval" as KaspiPricingRule["mode"],
    max_changes_per_day: "3",
  });
  const [competitorPrices, setCompetitorPrices] = useState<
    Record<string, string>
  >({});
  const [selectedRuleIds, setSelectedRuleIds] = useState<Array<string>>([]);
  const [bulkRuleStatus, setBulkRuleStatus] = useState("");
  const [bulkRuleMinPrice, setBulkRuleMinPrice] = useState("");
  const [bulkRuleStepAmount, setBulkRuleStepAmount] = useState("");
  const [bulkRuleMaxChanges, setBulkRuleMaxChanges] = useState("");
  const [bulkRuleDisableAutopilot, setBulkRuleDisableAutopilot] =
    useState(false);
  const rulesQuery = useQuery({
    queryKey: ["kaspi-pricing-rules", business?.id],
    queryFn: () => kaspiPricingApi.rules.list({ business: business?.id }),
    enabled: Boolean(business?.id),
  });
  const recommendationsQuery = useQuery({
    queryKey: ["kaspi-pricing-recommendations", business?.id],
    queryFn: () =>
      kaspiPricingApi.recommendations.list({ business: business?.id }),
    enabled: Boolean(business?.id),
  });
  const competitorOffersQuery = useQuery({
    queryKey: ["kaspi-competitor-offers", business?.id],
    queryFn: () =>
      kaspiPricingApi.competitorOffers.list({ business: business?.id }),
    enabled: Boolean(business?.id),
  });
  const createRule = useMutation({
    mutationFn: () => {
      if (!business?.id) throw new Error("Business is required.");
      return kaspiPricingApi.rules.create({
        business: business.id,
        product_sku: form.product_sku,
        product_name: form.product_name,
        current_price: form.current_price,
        min_price: form.min_price,
        step_amount: form.step_amount,
        mode: form.mode,
        max_changes_per_day: Number(form.max_changes_per_day || 3),
      });
    },
    onSuccess: () => {
      setForm({
        product_sku: "",
        product_name: "",
        current_price: "",
        min_price: "",
        step_amount: "1",
        mode: "approval",
        max_changes_per_day: "3",
      });
      queryClient.invalidateQueries({ queryKey: ["kaspi-pricing-rules"] });
    },
  });
  const recommend = useMutation({
    mutationFn: (rule: KaspiPricingRule) => {
      const manualPrice = competitorPrices[String(rule.id)] || "";
      return kaspiPricingApi.rules.recommend({
        id: rule.id,
        competitorPrice: manualPrice || undefined,
        competitorName: manualPrice ? "Competitor" : undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kaspi-pricing-rules"] });
      queryClient.invalidateQueries({
        queryKey: ["kaspi-pricing-recommendations"],
      });
      queryClient.invalidateQueries({ queryKey: ["kaspi-competitor-offers"] });
    },
  });
  const collectOffers = useMutation({
    mutationFn: (rule: KaspiPricingRule) =>
      kaspiPricingApi.rules.collectOffers({ id: rule.id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kaspi-pricing-rules"] });
      queryClient.invalidateQueries({
        queryKey: ["kaspi-pricing-recommendations"],
      });
      queryClient.invalidateQueries({ queryKey: ["kaspi-competitor-offers"] });
    },
  });
  const apply = useMutation({
    mutationFn: (recommendation: KaspiPricingRecommendation) =>
      kaspiPricingApi.recommendations.apply(recommendation.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kaspi-pricing-rules"] });
      queryClient.invalidateQueries({
        queryKey: ["kaspi-pricing-recommendations"],
      });
      queryClient.invalidateQueries({ queryKey: ["kaspi-price-change-logs"] });
    },
  });
  const enableAutopilot = useMutation({
    mutationFn: (rule: KaspiPricingRule) =>
      kaspiPricingApi.rules.enableAutopilot(rule.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kaspi-pricing-rules"] });
    },
  });
  const disableAutopilot = useMutation({
    mutationFn: (rule: KaspiPricingRule) =>
      kaspiPricingApi.rules.disableAutopilot(rule.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kaspi-pricing-rules"] });
    },
  });
  const bulkUpdateRules = useMutation({
    mutationFn: () =>
      kaspiPricingApi.rules.bulkUpdate({
        ruleIds: selectedRuleIds.map((id) => Number(id)),
        status: bulkRuleStatus
          ? (bulkRuleStatus as KaspiPricingRule["status"])
          : undefined,
        minPrice: bulkRuleMinPrice || undefined,
        stepAmount: bulkRuleStepAmount || undefined,
        maxChangesPerDay: bulkRuleMaxChanges
          ? Number(bulkRuleMaxChanges)
          : undefined,
        disableAutopilot: bulkRuleDisableAutopilot,
      }),
    onSuccess: () => {
      setSelectedRuleIds([]);
      setBulkRuleStatus("");
      setBulkRuleMinPrice("");
      setBulkRuleStepAmount("");
      setBulkRuleMaxChanges("");
      setBulkRuleDisableAutopilot(false);
      queryClient.invalidateQueries({ queryKey: ["kaspi-pricing-rules"] });
    },
  });
  const rules = rulesQuery.data || [];
  const latestRecommendations = useMemo(() => {
    const map = new Map<string, KaspiPricingRecommendation>();
    for (const item of recommendationsQuery.data || []) {
      const key = String(item.rule);
      if (!map.has(key)) map.set(key, item);
    }
    return map;
  }, [recommendationsQuery.data]);
  const latestOffers = useMemo(() => {
    const map = new Map<string, KaspiCompetitorOffer>();
    for (const item of competitorOffersQuery.data || []) {
      const key = String(item.rule);
      const current = map.get(key);
      if (!current || Number(item.price) < Number(current.price))
        map.set(key, item);
    }
    return map;
  }, [competitorOffersQuery.data]);
  return {
    form,
    setForm,
    competitorPrices,
    setCompetitorPrices,
    selectedRuleIds,
    setSelectedRuleIds,
    bulkRuleStatus,
    setBulkRuleStatus,
    bulkRuleMinPrice,
    setBulkRuleMinPrice,
    bulkRuleStepAmount,
    setBulkRuleStepAmount,
    bulkRuleMaxChanges,
    setBulkRuleMaxChanges,
    bulkRuleDisableAutopilot,
    setBulkRuleDisableAutopilot,
    rulesQuery,
    recommendationsQuery,
    competitorOffersQuery,
    createRule,
    recommend,
    collectOffers,
    apply,
    enableAutopilot,
    disableAutopilot,
    bulkUpdateRules,
    rules,
    latestRecommendations,
    latestOffers,
  };
}
