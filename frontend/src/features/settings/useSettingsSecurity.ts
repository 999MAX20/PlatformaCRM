import { useQuery } from "@tanstack/react-query";

import { securityApi } from "../../api/security";

import { useActiveBusiness } from "../../hooks/useBusiness";

type Context = {
  business: ReturnType<typeof useActiveBusiness>["business"];
  canViewAudit: boolean;
  activeSettingsSection: string;
};

export function useSettingsSecurity({ business, canViewAudit, activeSettingsSection }: Context) {
const auditLogs = useQuery({
    queryKey: ["security-audit", business?.id],
    queryFn: () => securityApi.audit({ business: business?.id }),
    enabled: activeSettingsSection === "security-center" && Boolean(business && canViewAudit),
    retry: false,
  });

const loginHistory = useQuery({
    queryKey: ["security-login-history", business?.id],
    queryFn: () => securityApi.loginHistory({ business: business?.id }),
    enabled: activeSettingsSection === "security-center" && Boolean(business && canViewAudit),
    retry: false,
  });

const supportGrants = useQuery({
    queryKey: ["security-support-grants", business?.id],
    queryFn: () => securityApi.supportGrants.listAll({ business: business?.id }),
    enabled: activeSettingsSection === "security-center" && Boolean(business && canViewAudit),
    retry: false,
  });
return { auditLogs, loginHistory, supportGrants };
}
