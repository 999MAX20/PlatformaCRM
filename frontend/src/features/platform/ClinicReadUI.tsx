import { useEffect } from "react";
import { normalizeAppError } from "../../api/appError";
import { Button } from "../../components/ui/Button";
import { useI18n } from "../../lib/i18n";
import type { ClinicKind, ClinicValue } from "../../api/platformClinic";
import { supportDate } from "../support/SupportUI";

export function useClinicReadDenial(error: unknown, onDenied: (error: unknown) => void) {
  useEffect(() => {
    if (error && normalizeAppError(error).category === "permission") onDenied(error);
  }, [error, onDenied]);
}

export const clinicStatuses: Record<ClinicKind, string[]> = {
  clients: [], leads: ["new", "in_progress", "appointment_created", "contacted", "closed", "lost"],
  deals: ["open", "won", "lost"], tasks: ["open", "in_progress", "waiting", "done", "cancelled"],
  appointments: ["created", "confirmed", "cancelled", "rescheduled", "completed", "no_show"],
  conversations: ["open", "closed", "archived"], payments: ["receipt", "refund"],
  connectors: ["draft", "connected", "pending_request", "setup_required", "provider_configuring", "error", "disconnected", "needs_attention", "syncing", "failed", "disabled", "expired_credentials"],
  channels: ["draft", "active", "paused", "error"],
};
export function ClinicPager({ page, count, size = 20, change }: { page: number; count: number; size?: number; change: (page: number) => void }) {
  const { t } = useI18n();
  return <div className="flex flex-wrap items-center justify-between gap-3 border-t border-platforma-border p-3" data-testid="clinic-pagination">
    <span className="text-sm" aria-live="polite">{t("pagination.total", { total: count })} · {t("pagination.currentPage", { page, pages: Math.max(1, Math.ceil(count / size)) })}</span>
    <div className="flex gap-2"><Button variant="secondary" disabled={page <= 1} onClick={() => change(page - 1)}>{t("pagination.previous")}</Button><Button variant="secondary" disabled={page * size >= count} onClick={() => change(page + 1)}>{t("pagination.next")}</Button></div>
  </div>;
}
export function ClinicValueView({ name, value, timezone }: { name: string; value: ClinicValue | undefined; timezone: string }) {
  const { t, language } = useI18n();
  if (value === null || value === undefined || value === "") return <>—</>;
  if (typeof value === "boolean") return <>{t(value ? "clinicCrm.value.yes" : "clinicCrm.value.no")}</>;
  if (Array.isArray(value)) return <>{value.join(", ") || "—"}</>;
  if (name.endsWith("_at") || name === "waiting_until") return <>{supportDate(String(value), language, timezone)}</>;
  const enumFields = ["status", "priority", "kind", "method", "channel", "direction", "sender_type", "source", "provider", "capability"];
  if (enumFields.includes(name)) { const key = `clinicCrm.value.${value}`; const label = t(key); return <>{label === key ? String(value) : label}</>; }
  return <>{String(value)}</>;
}
