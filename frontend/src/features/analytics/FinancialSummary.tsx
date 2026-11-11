import { Link } from "react-router";
import { useAuth } from "../auth/AuthProvider";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { hasPermission } from "../../lib/permissions";
import { StatusNotice } from "../../components/ui/StatusNotice";
import { Surface } from "../../components/ui/Card";
import { formatDateTime, formatMoney } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import type { FinancialReport } from "../../types";

const reasons = new Set([
  "no_source", "unsupported_source", "multiple_sources", "permission_denied",
  "source_unavailable", "initial_sync", "no_verified_snapshot", "sync_failed",
  "sync_stopped", "updating", "snapshot_not_refreshed", "sync_overdue", "currency_mismatch",
]);

export function FinancialStatus({ report, compact = false, inNotice = false }: { report?: FinancialReport; compact?: boolean; inNotice?: boolean }) {
  const { t, language } = useI18n();
  const reason = report?.reason && reasons.has(report.reason) ? report.reason : "source_unavailable";
  return (
    <span className={`block ${compact ? "space-y-0.5 text-[11px] leading-4" : "space-y-1 text-xs leading-5"}`} data-testid="financial-status">
      {report?.state !== "available" ? (
        <span className={`block ${inNotice ? "text-inherit" : report?.state === "stale" ? "font-semibold text-platforma-warning" : "text-platforma-subtle"}`}>
          {report?.state === "stale" ? `${t("finance.stale")} ` : ""}{t(`finance.reason.${reason}`)}
        </span>
      ) : null}
      {report?.source ? <span className="block break-words">{t("finance.source", { name: report.source.provider === "manual" ? t("aiHistory.manual") : report.source.name })}</span> : null}
      {report ? <span className="block">{t("finance.period", { start: report.period.start, end: report.period.end })}</span> : null}
      {report?.last_successful_sync_at ? (
        <span className="block">{t("finance.asOf", { at: formatDateTime(report.last_successful_sync_at, undefined, true, language) })}</span>
      ) : null}
      {report?.last_recorded_at ? <span className="block">{t("aiHistory.lastRecorded", { at: formatDateTime(report.last_recorded_at, undefined, true, language) })}</span> : null}
    </span>
  );
}

export function FinancialSummary({ report }: { report: FinancialReport }) {
  const { t, language } = useI18n();
  const { user } = useAuth();
  const { business } = useActiveBusiness();
  const canViewConnections = hasPermission(user, business?.id, "integrations");
  const connectionReason = Boolean(report.reason && reasons.has(report.reason) && report.reason !== "permission_denied" && report.source?.provider !== "manual");
  return (
    <Surface as="section" padding="md" data-testid="financial-summary">
      <h2 className="text-base font-bold text-platforma-ink">{t(report.source?.provider === "manual" ? "aiHistory.manual" : "finance.title")}</h2>
      {report.state !== "available" ? <div className="mt-3" data-testid="financial-prerequisite">
        <StatusNotice tone={report.state === "stale" ? "warning" : "info"}
          title={t(report.state === "stale" ? "finance.stale" : "finance.unavailable")}
          details={<FinancialStatus report={report} inNotice />}
          action={connectionReason ? canViewConnections
            ? <Link className="platforma-focus-ring underline underline-offset-4" to="/app/integrations">{t("serviceStatus.openConnections")}</Link>
            : <span>{t("serviceStatus.askAdmin")}</span> : undefined}
        />
      </div> : <div className="mt-3 text-platforma-subtle"><FinancialStatus report={report} /></div>}
      {report.state !== "unavailable" ? (
        <dl className="mt-4 grid gap-4 sm:grid-cols-3">
          {(["receipts", "refunds", "net_receipts"] as const).map((key) => (
            <div key={key}>
              <dt className="text-sm text-platforma-subtle">{t(`finance.${key}`)}</dt>
              <dd className="mt-1 text-2xl font-semibold tabular-nums text-platforma-ink">{formatMoney(report[key], report.currency, language)}</dd>
            </div>
          ))}
        </dl>
      ) : null}
    </Surface>
  );
}
