import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";

import { businessConnectorsApi } from "../../api/connectors";
import { getApiErrorMessage } from "../../api/client";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";
import { useAuth } from "../auth/AuthProvider";
import { ProviderCard } from "./components/ProviderCard";
import { integrationProviderCatalog } from "./config/providerCatalog";
import { GoogleSheetsCard } from "./components/GoogleSheetsCard";
import { GoogleCalendarCard } from "./components/GoogleCalendarCard";

export function IntegrationsPage({ embedded = false }: { embedded?: boolean }) {
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
    <div className={embedded ? "flex w-full min-w-0 flex-col gap-4 p-4 sm:p-5" : "mx-auto flex min-h-[calc(100dvh-12rem)] w-full max-w-2xl flex-col justify-center gap-4 py-4 lg:min-h-[calc(100dvh-6rem)]"}>
      {pageError ? <ErrorState error={pageError} message={getApiErrorMessage(pageError)} /> : null}
      {canManage && <Link to="/app/integrations/import" className="rounded-control border border-platforma-border bg-surface-card px-4 py-3 text-sm font-semibold text-brand-700 hover:bg-surface-hover">{t("importWorkspace.title")}</Link>}
      <div className="grid items-stretch gap-3 sm:grid-cols-2">
        {canManage && <GoogleSheetsCard key={`${user?.id}:${business.id}`} businessId={business.id} />}
        {canManage && <GoogleCalendarCard key={`calendar:${user?.id}:${business.id}`} businessId={business.id} />}
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
