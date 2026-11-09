import { useQuery } from "@tanstack/react-query";
import { Activity } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router";
import { getServiceStatus } from "../../api/serviceStatus";
import { useAuth } from "../../features/auth/AuthProvider";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Modal";
import { StatusNotice } from "../ui/StatusNotice";

export function ServiceStatusNotice() {
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [business?.id, user?.id]);
  const status = useQuery({
    queryKey: ["service-status", business?.id, user?.id],
    queryFn: ({ signal }) => getServiceStatus(business!.id, signal),
    enabled: Boolean(business), staleTime: 30_000, refetchInterval: 60_000,
    refetchOnWindowFocus: true, retry: false,
  });
  if (!business) return null;
  const state = status.isError ? "unknown" : status.data?.status || "unknown";
  const label = status.isPending ? t("common.loading") : t(`serviceStatus.platform.${state}`);
  const affected = status.data?.components.filter(item => item.state === "degraded")
    .map(item => t(`serviceStatus.component.${item.component}`)).join(", ") || "";

  return <>
    <Button variant="ghost" className="relative h-10 w-10 shrink-0 px-0"
      data-testid="service-status-trigger" aria-label={label} title={label}
      aria-haspopup="dialog" aria-expanded={open} onClick={() => setOpen(true)}>
      <Activity size={20} aria-hidden="true" />
      <span aria-hidden="true" className={`absolute right-1 top-1 h-2 w-2 rounded-full ${state === "healthy" ? "bg-platforma-success" : state === "degraded" ? "bg-platforma-warning" : "bg-platforma-faint"}`} />
      <span className="sr-only" role="status" aria-live="polite">{label}</span>
    </Button>
    <Modal open={open} onClose={() => setOpen(false)} title={t("serviceStatus.title")}>
      <StatusNotice data-testid="service-status-notice" role="status" ariaLive="polite"
        tone={state === "healthy" ? "success" : state === "degraded" ? "warning" : "info"}
        title={state === "healthy" || status.isPending ? label : t(`serviceStatus.${state}.title`)}
        description={t(`serviceStatus.${state === "healthy" ? "recovered" : state}.text`, { components: affected })}
        action={<Button variant="secondary" onClick={() => void status.refetch()} isLoading={status.isFetching}>{t("common.refresh")}</Button>}
        details={state !== "healthy" ? <Link className="platforma-focus-ring underline underline-offset-4" to="/app/support" onClick={() => setOpen(false)}>{t("serviceStatus.openSupport")}</Link> : undefined}
      />
    </Modal>
  </>;
}
