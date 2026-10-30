import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { kaspiPricingApi } from "../../api/pricing";

import { useActiveBusiness } from "../../hooks/useBusiness";

export function usePricingSafety(
  business: ReturnType<typeof useActiveBusiness>["business"],
) {
  const queryClient = useQueryClient();
  const controlQuery = useQuery({
    queryKey: ["kaspi-pricing-control", business?.id],
    queryFn: () => {
      if (!business?.id) throw new Error("Business is required.");
      return kaspiPricingApi.control.current(business.id);
    },
    enabled: Boolean(business?.id),
  });
  const alertsQuery = useQuery({
    queryKey: ["kaspi-pricing-alerts", business?.id],
    queryFn: () =>
      kaspiPricingApi.alerts.list({ business: business?.id, status: "open" }),
    enabled: Boolean(business?.id),
  });
  const emergencyStop = useMutation({
    mutationFn: () => {
      if (!business?.id) throw new Error("Business is required.");
      return kaspiPricingApi.control.emergencyStop({
        business: business.id,
        reason: "Stopped from PlatformaCRM workspace.",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kaspi-pricing-control"] });
      queryClient.invalidateQueries({ queryKey: ["kaspi-pricing-alerts"] });
    },
  });
  const resumePricing = useMutation({
    mutationFn: () => {
      if (!business?.id) throw new Error("Business is required.");
      return kaspiPricingApi.control.resume(business.id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kaspi-pricing-control"] });
      queryClient.invalidateQueries({ queryKey: ["kaspi-pricing-alerts"] });
    },
  });
  const alerts = alertsQuery.data || [];
  const control = controlQuery.data;
  return {
    controlQuery,
    alertsQuery,
    emergencyStop,
    resumePricing,
    alerts,
    control,
  };
}
