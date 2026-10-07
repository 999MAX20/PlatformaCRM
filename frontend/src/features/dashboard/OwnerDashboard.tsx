import { ArrowRight } from "lucide-react";
import { Link } from "react-router";

import type { AIOwnerDailyBriefResponse } from "../../api/ai";
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
  ownerBrief?: AIOwnerDailyBriefResponse;
  ownerBriefError: unknown;
  canViewAiAnalyst: boolean;
};

export function OwnerDashboard({ dashboard, metricsError, metricsLoading, retryMetrics, canViewAnalytics,
  ownerBrief, ownerBriefError, canViewAiAnalyst }: Props) {
  const { t } = useI18n();
  const categoryKeys: Record<string, string> = { stale_leads: "staleLead", overdue_tasks: "overdueTask",
    unanswered_conversations: "unansweredConversation", stalled_deals: "stalledDeal", failed_connectors: "failedConnector" };
  const financial = metricsError ? undefined : dashboard?.financial;
  const recommendations = ownerBriefError ? [] : (ownerBrief?.recommendations || []).filter((item) =>
    item.source_ids.some((id) => ownerBrief?.sources.some((source) => source.id === id)),
  ).slice(0, 3).map((item) => {
    const labels = item.source_ids.map((id) => ownerBrief?.sources.find((source) => source.id === id)?.label).filter(Boolean);
    const key = categoryKeys[item.category];
    return { ...item, labels, label: key ? t(`dashboard.ownerBrief.${key}.title`, { source: labels[0] || t("dashboard.ownerBriefFallbackSource") }) : item.label,
      description: key ? t(`dashboard.ownerBrief.${key}.text`) : item.description };
  });
  const members = metricsError ? [] : (dashboard?.manager_performance?.rows || []).filter((member) =>
    !["owner", "business_owner"].includes(member.role) && (member.assigned_leads > 0 || member.overdue_tasks > 0),
  ).sort((a, b) => b.overdue_tasks - a.overdue_tasks || b.assigned_leads - a.assigned_leads).slice(0, 4);

  return <>
    {canViewAnalytics ? <Surface as="section" padding="lg" data-testid="dashboard-finance">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-platforma-text">{t("finance.net_receipts")}</h2>
          <div className="mt-2 text-platforma-subtle"><FinancialStatus report={financial} compact /></div>
          {financial?.as_of ? <p className="mt-1 text-xs text-platforma-subtle">{t("finance.asOf", { at: formatDateTime(financial.as_of, undefined, true) })}</p> : null}
        </div>
        {metricsLoading ? <LoadingState /> : <p className="text-2xl font-semibold tabular-nums text-platforma-text">{
          financial && financial.state !== "unavailable" ? formatMoney(financial.net_receipts, financial.currency) : t("finance.unavailable")
        }</p>}
        {metricsError ? <Button size="sm" variant="secondary" onClick={retryMetrics}>{t("common.retry")}</Button>
          : <Link to="/app/analytics" className="platforma-focus-ring inline-flex min-h-9 items-center gap-2 rounded-control text-sm font-semibold text-brand-700">{t("dashboard.openFinancialReport")}<ArrowRight size={15} aria-hidden="true" /></Link>}
      </div>
      {metricsError ? <p role="alert" className="mt-3 text-sm text-platforma-warning">{t("dashboard.ownerAnalyticsError")}</p> : null}
    </Surface> : null}
    {canViewAiAnalyst && recommendations.length > 0 ? <Surface as="section" padding="md" variant="ai">
      <h2 className="text-sm font-semibold text-platforma-text">{t("dashboard.aiBrief.title")}</h2>
      <ul className="mt-2 divide-y divide-ai-100">{recommendations.map((recommendation) => <li key={recommendation.id} className="py-2">
        <Link to={recommendation.href} className="platforma-focus-ring block rounded-control text-sm font-semibold text-platforma-text">{recommendation.label}</Link>
        <p className="mt-1 text-xs text-platforma-subtle">{recommendation.description}</p>
        <p className="mt-1 text-xs text-platforma-subtle">{t("dashboard.ownerBriefSourceIds", { ids: recommendation.labels.join(", ") })}</p>
      </li>)}</ul>
    </Surface> : null}
    {canViewAiAnalyst && ownerBriefError ? <p role="status" className="text-xs text-platforma-subtle">{t("dashboard.ownerBriefUnavailableText")}</p> : null}
    {canViewAnalytics && members.length > 0 ? <Surface padding="md">
      <details>
        <summary className="platforma-focus-ring cursor-pointer rounded-control text-sm font-semibold text-platforma-text">{t("dashboard.teamWorkload")}</summary>
        <ul className="mt-3 divide-y divide-platforma-border">{members.map((member) => <li key={member.user_id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
          <span className="font-medium text-platforma-text">{member.full_name || member.email}</span>
          <span className="text-xs text-platforma-subtle">{t("analytics.assignedLeads")}: {member.assigned_leads} · {t("analytics.overdueTasks")}: {member.overdue_tasks}</span>
        </li>)}</ul>
      </details>
    </Surface> : null}
  </>;
}
