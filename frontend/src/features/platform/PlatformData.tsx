import { Link } from "react-router";
import { cn } from "../../lib/cn";
import { useI18n } from "../../lib/i18n";
import type { PlatformClinicService, PlatformMerchantOperations } from "../../types";
import { normalizeAppError } from "../../api/appError";
import { ErrorState, ForbiddenState } from "../../components/ui/StateViews";
import { Button } from "../../components/ui/Button";

export function PlatformLoadError({ error, message, onRetry }: { error: unknown; message: string; onRetry: () => void }) {
  const { t } = useI18n();
  const normalized = normalizeAppError(error);
  if (normalized.category === "permission") return <ForbiddenState error={normalized} />;
  return <ErrorState error={error} message={message} action={<Button variant="secondary" onClick={onRetry}>{t("platform.merchantDetail.refresh")}</Button>} />;
}

export function valueOrUnknown(value: number | null | undefined) {
  return value ?? "—";
}

export function platformDate(value: string | null | undefined, language: string) {
  if (!value) return "—";
  return new Date(value).toLocaleString(language === "kk" ? "kk-KZ" : language === "en" ? "en-US" : "ru-RU", {
    year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", timeZoneName: "short",
  });
}

export function PlatformMetric({ label, value, href }: { label: string; value: number | string | null | undefined; href?: string }) {
  const { t } = useI18n();
  return <div className="min-w-0 p-3">
    <dt className="text-sm text-platforma-subtle">{href ? <Link to={href} className="platforma-focus-ring rounded-control hover:text-brand-700 hover:underline">{label}</Link> : label}</dt>
    <dd className="mt-1 text-2xl font-semibold tabular-nums text-platforma-text" aria-label={value == null ? t("platform.workspace.unknown") : undefined}>{value ?? "—"}</dd>
  </div>;
}

export function PlatformServiceBadge({ service }: { service?: PlatformClinicService }) {
  const { t } = useI18n();
  const status = service?.status || "unknown";
  return <span data-testid="clinic-service-state" className={cn("inline-flex rounded-control border px-2 py-1 text-xs font-medium",
    status === "healthy" ? "border-platforma-success/20 bg-[var(--platforma-success-soft)] text-platforma-success" :
    status === "degraded" ? "border-platforma-warning/20 bg-[var(--platforma-warning-soft)] text-platforma-warning" :
    "border-platforma-border bg-surface-muted text-platforma-subtle")}>{t(`platform.workspace.service.${status}`)}</span>;
}

export function PlatformRecordedSignals({ operations }: { operations?: PlatformMerchantOperations }) {
  const { t } = useI18n();
  const unknown = !operations || !!operations.unavailable_sources?.length;
  const failures = (operations?.failed_connectors ?? 0) + (operations?.form_errors ?? 0);
  return <div data-testid="clinic-recorded-signals" className="space-y-2 text-sm">
    {unknown && <p className="text-platforma-subtle">{t("platform.workspace.partial")}</p>}
    {!!operations?.failed_connectors && <p className="text-platforma-warning">{t("platform.workspace.failedSources", { count: operations.failed_connectors })}</p>}
    {!!operations?.form_errors && <p className="text-platforma-warning">{t("platform.workspace.formErrors", { count: operations.form_errors })}</p>}
    {!unknown && failures === 0 && <p className="text-platforma-subtle">{t("platform.workspace.noRecordedFailures")}</p>}
  </div>;
}
