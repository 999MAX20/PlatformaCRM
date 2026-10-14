import { useQuery } from "@tanstack/react-query";
import { getServiceStatus } from "../../api/serviceStatus";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { Button } from "../ui/Button";
import { StatusNotice } from "../ui/StatusNotice";

export function ServiceStatusNotice() {
  const { business } = useActiveBusiness();
  const { t } = useI18n();
  const status = useQuery({
    queryKey: ["service-status", business?.id],
    queryFn: ({ signal }) => getServiceStatus(business!.id, signal),
    enabled: Boolean(business), staleTime: 30_000, refetchInterval: 60_000, refetchOnWindowFocus: true, retry: false,
  });
  if (!business || status.isPending) return null;
  const data = status.data;
  const state = status.isError ? "unknown" : data?.status || "unknown";
  const recovered = state === "healthy" && data?.components.some(item => item.recovered_at &&
    Date.parse(data.checked_at) - Date.parse(item.recovered_at) < data.max_age_seconds * 1000);
  if (state === "healthy" && !recovered) return null;
  const affected = data?.components.filter(item => item.state === "degraded").map(item => t(`serviceStatus.component.${item.component}`)).join(", ");
  return <StatusNotice data-testid="service-status-notice" compact role="status" ariaLive="polite"
    className="m-3" tone={recovered ? "success" : state === "degraded" ? "warning" : "info"}
    title={t(`serviceStatus.${recovered ? "recovered" : state}.title`)}
    description={t(`serviceStatus.${recovered ? "recovered" : state}.text`, { components: affected || "" })}
    action={<Button size="sm" variant="secondary" onClick={() => status.refetch()} isLoading={status.isFetching}>{t("common.refresh")}</Button>} />;
}
