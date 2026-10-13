import { useQuery } from "@tanstack/react-query";

import { businessConnectorsApi } from "../../api/connectors";
import { getApiErrorMessage } from "../../api/client";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";
import { useAuth } from "../auth/AuthProvider";
import { ProviderCard } from "./components/ProviderCard";
import { integrationProviderCatalog } from "./config/providerCatalog";

export function IntegrationsPage() {
  const { t } = useI18n();
  const { user } = useAuth();
  const { business, isLoading: isBusinessLoading } = useActiveBusiness();
  const canManage = hasPermission(user, business?.id, "integrations", "manage");
  const capabilities = useQuery({
    queryKey: ["connector-capabilities"],
    queryFn: businessConnectorsApi.capabilities,
  });
  const connectors = useQuery({
    queryKey: ["business-connectors", business?.id],
    queryFn: businessConnectorsApi.list,
    enabled: Boolean(business?.id),
  });

  if (isBusinessLoading || capabilities.isLoading || connectors.isLoading) {
    return <LoadingState scope="page" />;
  }

  if (!business) {
    return <EmptyState title={t("integrations.page.noBusinessTitle")} description={t("integrations.page.noBusinessDescription")} />;
  }

  const pageError = capabilities.error || connectors.error;

  return (
    <div className="space-y-4 p-4 sm:p-5">
      {pageError ? <ErrorState error={pageError} message={getApiErrorMessage(pageError)} /> : null}
      <div className="grid items-stretch gap-4 md:grid-cols-2">
        {integrationProviderCatalog.map((provider) => (
          <ProviderCard
            key={provider.provider}
            businessId={business.id}
            canManage={canManage}
            capability={capabilities.data?.find((item) => item.provider === provider.provider)}
            connector={connectors.data?.find((item) => item.provider === provider.provider)}
            provider={provider}
          />
        ))}
      </div>
    </div>
  );
}
