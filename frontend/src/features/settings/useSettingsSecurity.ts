import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { securityApi } from "../../api/security";

import { useActiveBusiness } from "../../hooks/useBusiness";

type Context = {
  business: ReturnType<typeof useActiveBusiness>["business"];
  canViewAudit: boolean;
  activeSettingsSection: string;
};

export function useSettingsSecurity({ business, canViewAudit, activeSettingsSection }: Context) {
const [securityFilters, setSecurityFilters] = useState({ period: "all", date_from: undefined as string | undefined, failedOnly: false, auditPage: 1, loginPage: 1 });
const auditLogs = useQuery({
    queryKey: ["security-audit", business?.id, securityFilters.date_from, securityFilters.auditPage],
    queryFn: () => securityApi.auditPage({ business: business?.id, date_from: securityFilters.date_from, page: securityFilters.auditPage }),
    enabled: activeSettingsSection === "security-center" && Boolean(business && canViewAudit),
    retry: false,
  });

const loginHistory = useQuery({
    queryKey: ["security-login-history", business?.id, securityFilters.date_from, securityFilters.failedOnly, securityFilters.loginPage],
    queryFn: () => securityApi.loginHistoryPage({ business: business?.id, date_from: securityFilters.date_from, status: securityFilters.failedOnly ? "failed" : undefined, page: securityFilters.loginPage }),
    enabled: activeSettingsSection === "security-center" && Boolean(business && canViewAudit),
    retry: false,
  });

const supportGrants = useQuery({
    queryKey: ["security-support-grants", business?.id],
    queryFn: () => securityApi.supportGrants.listAll({ business: business?.id }),
    enabled: activeSettingsSection === "security-center" && Boolean(business && canViewAudit),
    retry: false,
  });
return { auditLogs, loginHistory, supportGrants, securityFilters, setSecurityFilters };
}
