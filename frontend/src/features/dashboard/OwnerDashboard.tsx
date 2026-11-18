import { Link } from "react-router";

import { normalizeAppError } from "../../api/appError";
import { Button } from "../../components/ui/Button";
import { Surface } from "../../components/ui/Card";
import { LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { formatDateTime, formatMoney } from "../../lib/format";
import type { OwnerDashboardMetrics } from "../../types";
import { FinancialStatus } from "../analytics/FinancialSummary";

type Props = {
  dashboard?: OwnerDashboardMetrics;
  metricsError: unknown;
  metricsLoading: boolean;
  retryMetrics: () => void;
  canViewAnalytics: boolean;
};

export function OwnerDashboard({ dashboard, metricsError, metricsLoading, retryMetrics, canViewAnalytics }: Props) {
  const { t, language } = useI18n();
  if (!canViewAnalytics) return null;
  const denied = Boolean(metricsError && ["permission", "authentication"].includes(normalizeAppError(metricsError).category));
  const financial = denied ? undefined : dashboard?.financial;

  return <Surface as="section" padding="lg" data-testid="dashboard-finance">
    <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
      <h2 className="text-base font-semibold text-platforma-text">{t("dashboard.financeToday")}</h2>
      {!denied ? <Link to="/app/analytics" className="platforma-focus-ring inline-flex min-h-11 items-center rounded-control text-sm font-semibold text-brand-700 hover:underline">{t("dashboard.openFinancialReport")}</Link> : null}
    </div>
    {metricsError ? <div role="alert" className="mt-2 flex flex-wrap items-center justify-between gap-3 text-sm text-platforma-warning">
      <p>{t(denied ? "dashboard.operationsNoAccess" : financial ? "dashboard.refreshFailed" : "dashboard.ownerAnalyticsError")}</p>
      {!denied ? <Button className="min-h-11" variant="secondary" onClick={retryMetrics}>{t("common.retry")}</Button> : null}
    </div> : null}
    {metricsLoading ? <LoadingState /> : financial ? <>
      {financial.state !== "unavailable" ? <dl className="my-4 grid gap-4 sm:grid-cols-3">
        {(["receipts", "refunds", "net_receipts"] as const).map(key => <div key={key}>
          <dt className="text-sm text-platforma-subtle">{t(`finance.${key}`)}</dt>
          <dd className="mt-1 break-words text-2xl font-semibold tabular-nums text-platforma-text">{formatMoney(financial[key], financial.currency, language)}</dd>
        </div>)}
      </dl> : <p className="my-3 text-sm font-medium text-platforma-text">{t("finance.unavailable")}</p>}
      <div className="mt-2 text-platforma-subtle"><FinancialStatus report={financial} /></div>
      {financial.as_of ? <p className="mt-1 text-xs text-platforma-subtle">{t("finance.asOf", { at: formatDateTime(financial.as_of, undefined, true, language) })}</p> : null}
    </> : !metricsError ? <p className="mt-3 text-sm text-platforma-subtle">{t("finance.unavailable")}</p> : null}
  </Surface>;
}
