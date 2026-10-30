import { useQuery } from "@tanstack/react-query";

import { billingApi } from "../../api/billing";

import { useActiveBusiness } from "../../hooks/useBusiness";

type Context = {
  business: ReturnType<typeof useActiveBusiness>["business"];
  canViewBilling: boolean;
  activeSettingsSection: string;
};

export function useSettingsBilling({ business, canViewBilling, activeSettingsSection }: Context) {
const entitlements = useQuery({
    queryKey: ["billing-entitlements", business?.id],
    queryFn: () => billingApi.entitlements(business!.id),
    enabled: activeSettingsSection === "usage" && Boolean(business && canViewBilling),
  });
return { entitlements };
}
