import { PlatformLoadError } from "./PlatformData";
import { useQuery } from "@tanstack/react-query";
import { Link, useLocation } from "react-router";
import { platformApi } from "../../api/platform";
import { Button } from "../../components/ui/Button";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { PlatformPageHeading } from "../../components/layout/PlatformPageHeading";
import { LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { PlatformMetric, platformDate } from "./PlatformData";
import { OverviewAttention } from "./OverviewAttention";
import { retainSupportData } from "../support/SupportUI";

export function PlatformOverviewPage() {
  const { t, language } = useI18n();
  const { hash } = useLocation();
  const overview = useQuery({ queryKey: ["platform-overview"], queryFn: platformApi.overview, refetchInterval: 30_000 });
  if (overview.isPending) return <LoadingState scope="page" />;
  if (!overview.data || (overview.isError && !retainSupportData(overview.error))) return <PlatformLoadError error={overview.error} message={t("platform.overview.error")} onRetry={() => overview.refetch()} />;
  const data = overview.data;
  const service = data.service_status;
  const locale = language === "en" ? "en-US" : language === "kk" ? "kk-KZ" : "ru-KZ";
  const mrr = data.mrr_estimate == null ? null : `${new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(Number(data.mrr_estimate))} ₸`;

  return <div className="space-y-4" data-testid="platform-overview-ready">
    <PlatformPageHeading title={t("platform.nav.overview")} />
    <div className="flex flex-wrap items-center justify-between gap-2">
      <p className="text-xs text-platforma-faint">{t("platform.workspace.snapshotAt", { date: platformDate(data.generated_at, language) })}</p>
      <Button variant="secondary" onClick={() => overview.refetch()} isLoading={overview.isFetching}>{t("platform.merchantDetail.refresh")}</Button>
    </div>
    {overview.isError && <PlatformLoadError error={overview.error} message={t("platform.overview.error")} onRetry={() => overview.refetch()} />}
    <details className="text-xs text-platforma-subtle" data-testid="platform-overview-service">
      <summary className="platforma-focus-ring w-fit cursor-pointer rounded-control py-1">{t(`serviceStatus.platform.${service?.status || "unknown"}`)}</summary>
      <div className="mt-2 flex flex-wrap items-center gap-3 rounded-control bg-surface-muted p-3">
        <span>{service?.businesses ? t("serviceStatus.platform.counts", service.businesses) : t("serviceStatus.unknown.text")}</span>
        <Link to="/platform/operations" className="platforma-focus-ring font-medium text-brand-700">{t("platform.nav.operations")}</Link>
      </div>
    </details>
    <OverviewAttention data={data.attention} />
    <Card>
      <CardHeader><h2 className="font-semibold">{t("platform.overview.errorsTitle")}</h2></CardHeader>
      <CardBody className="p-2">
        {!!data.operations_summary.unavailable_sources?.length && <p role="status" className="px-3 pb-2 text-sm text-platforma-subtle">{t("platform.workspace.partial")}</p>}
        <dl className="grid grid-cols-2 lg:grid-cols-4">
          <PlatformMetric label={t("platform.workspace.failedJobs")} value={data.errors.count} />
          <PlatformMetric label={t("platform.workspace.failedSourcesTitle")} value={data.operations_summary.failed_connectors} />
          <PlatformMetric label={t("platform.overview.formErrors")} value={data.operations_summary.form_errors_30d} />
          <PlatformMetric label={t("platform.overview.handoffConversations")} value={data.operations_summary.handoff_conversations} />
        </dl>
      </CardBody>
    </Card>
    <div className="divide-y divide-platforma-border rounded-card border border-platforma-border bg-surface-card">
      <details data-testid="platform-usage">
        <summary className="platforma-focus-ring cursor-pointer rounded-control px-4 py-3 font-semibold">{t("platform.workspace.activity")}</summary>
        <CardBody className="p-2"><dl className="grid grid-cols-2 sm:grid-cols-3">
          <PlatformMetric label={t("platform.overview.totalMerchants")} value={data.total_businesses} href="/platform/merchants" />
          <PlatformMetric label={t("platform.overview.activeMerchants")} value={data.active_businesses} href="/platform/merchants?status=active" />
          <PlatformMetric label={t("platform.overview.trialMerchants")} value={data.trial_businesses} href="/platform/merchants?status=trial" />
          <PlatformMetric label={t("platform.overview.newLeads")} value={data.operations_summary.new_leads_30d} />
          <PlatformMetric label={t("platform.overview.conversations")} value={data.conversations_30d} />
          <PlatformMetric label={t("platform.overview.aiRequests")} value={data.ai_requests_30d} />
          <PlatformMetric label={t("platform.overview.activeChannels")} value={data.active_bot_channels} />
          <PlatformMetric label={t("platform.overview.users")} value={data.total_users} />
          <PlatformMetric label={t("platform.overview.bots")} value={data.bot_count} />
        </dl></CardBody>
      </details>
      <details id="finance" open={hash === "#finance" || undefined} className="scroll-mt-20" data-testid="platform-finance">
        <summary className="platforma-focus-ring cursor-pointer rounded-control px-4 py-3 font-semibold">{t("platform.workspace.finance")}</summary>
        <CardBody className="space-y-3 p-2">
          <dl className="grid grid-cols-2">
            <PlatformMetric label={t("platform.overview.mrr")} value={mrr} />
            <PlatformMetric label={t("platform.overview.activeSubscriptions")} value={data.active_subscriptions} />
          </dl>
          <p className="px-3 pb-3 text-xs leading-5 text-platforma-subtle">{t("platform.overview.mrrText")}</p>
        </CardBody>
      </details>
    </div>
    <p className="text-xs text-platforma-faint">{t("platform.workspace.unknownLegend")}</p>
  </div>;
}
