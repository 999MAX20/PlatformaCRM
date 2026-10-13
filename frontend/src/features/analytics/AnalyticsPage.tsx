import { useMutation, useQuery } from "@tanstack/react-query";
import { Download, HelpCircle, RefreshCw } from "lucide-react";
import { useState, useEffect } from "react";
import { useSearchParams } from "react-router";
import { analyticsApi } from "../../api/analytics";
import { analyticsExports } from "../../api/analyticsExports";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { Button } from "../../components/ui/Button";
import { DateRangePicker, isCalendarDate, type DateRangeValue } from "../../components/ui/DateRangePicker";
import { Dialog } from "../../components/ui/Overlay";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { dateInTimeZone } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import type { Business, Id } from "../../types";
import type { WorkspaceReport } from "../../types/analyticsWorkspace";
import { useAuth } from "../auth/AuthProvider";
import { FinancialSummary } from "./FinancialSummary";
import { Overview, ServicesTable, SourcesTable, TeamTable } from "./WorkspaceSections";

const tabs = ["overview", "sources", "services", "team", "finance"] as const;
type Tab = typeof tabs[number];
const reports: Record<Tab, WorkspaceReport> = {
  overview: "workspace_overview", sources: "workspace_sources", services: "workspace_services", team: "workspace_team", finance: "workspace_finance",
};
function recentPeriod(today: string, days: number) {
  const from = new Date(`${today}T12:00:00Z`);
  from.setUTCDate(from.getUTCDate() - days + 1);
  return { from: from.toISOString().slice(0, 10), to: today };
}

export function AnalyticsPage() {
  const { business, isLoading } = useActiveBusiness();
  const { user } = useAuth();
  const { t } = useI18n();
  if (isLoading) return <LoadingState scope="page" />;
  if (!business || !user) return <EmptyState title={t("analytics.noBusiness")} />;
  return <AnalyticsWorkspacePage key={`${user.id}:${business.id}`} business={business} userId={user.id} />;
}

function AnalyticsWorkspacePage({ business, userId }: { business: Business; userId: Id }) {
  const { t, language } = useI18n();
  const { setPageHeader } = usePageHeader();
  const [params, setParams] = useSearchParams();
  const today = dateInTimeZone(new Date(), business.timezone);
  const defaults = recentPeriod(today, 30);
  const start = params.get("start") || defaults.from;
  const end = params.get("end") || defaults.to;
  const active = tabs.includes(params.get("tab") as Tab) ? params.get("tab") as Tab : "overview";
  const context = `${userId}:${business.id}:${start}:${end}:${active}`;
  const [draft, setDraft] = useState<DateRangeValue>({ from: start, to: end });
  const [help, setHelp] = useState(false);
  const [periodOpen, setPeriodOpen] = useState(false);
  useEffect(() => { setPageHeader({ title: t("analytics.title") }); return () => setPageHeader(null); }, [setPageHeader, t]);
  const metrics = useQuery({
    queryKey: ["analytics-workspace", userId, business.id, start, end],
    queryFn: () => analyticsApi.workspace(business.id, { start, end }), retry: false,
  });
  const exportMutation = useMutation({
    mutationFn: async () => ({ context, job: await analyticsExports.request(business.id, { start, end }, reports[active]) }),
  });
  const receipt = exportMutation.data?.context === context ? exportMutation.data : undefined;
  const jobId = receipt?.job?.id;
  const job = useQuery({
    queryKey: ["analytics-export", userId, business.id, jobId],
    queryFn: () => analyticsExports.job(jobId!, business.id), enabled: Boolean(jobId), retry: false,
    refetchInterval: query => query.state.error || ["succeeded", "failed"].includes(query.state.data?.status || "") ? false : 3000,
  });
  const download = useMutation({ mutationFn: () => analyticsExports.download(jobId!, business.id) });
  const currentJob = job.data || receipt?.job;
  const canExport = Boolean(metrics.data) && !metrics.error && (active !== "team" || metrics.data?.team.available);
  function changeTab(tab: Tab) { setParams(previous => { const next = new URLSearchParams(previous); next.set("tab", tab); return next; }); }
  function applyPeriod() {
    setParams(previous => { const next = new URLSearchParams(previous); next.set("start", draft.from); next.set("end", draft.to); return next; });
    setPeriodOpen(false);
  }
  function openPeriod() { setDraft({ from: start, to: end }); setPeriodOpen(true); }
  const dateLabel = (day: string) => isCalendarDate(day)
    ? new Intl.DateTimeFormat(language, { day: "numeric", month: language === "kk" ? "numeric" : "short", year: "numeric", timeZone: "UTC" }).format(new Date(`${day}T12:00:00Z`)) : day;

  return <div className="space-y-4" data-testid="analytics-workspace">
    <h1 className="sr-only">{t("analytics.title")}</h1>
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-platforma-border pb-3">
      <nav aria-label={t("analyticsWorkspace.sections")} className="flex flex-wrap gap-1">
        {tabs.map(tab => <Button key={tab} variant={active === tab ? "secondary" : "ghost"} aria-current={active === tab ? "page" : undefined} onClick={() => changeTab(tab)} className="min-h-11 px-3">{t(`analyticsWorkspace.${tab}`)}</Button>)}
      </nav>
      <div className="flex w-full flex-wrap items-center gap-2 xl:w-auto">
        <Button variant="secondary" onClick={openPeriod} className="min-h-11" aria-label={t("analyticsWorkspace.period")}>{dateLabel(start)} — {dateLabel(end)}</Button>
        <Button variant="secondary" disabled={!canExport} isLoading={exportMutation.isPending} onClick={() => exportMutation.mutate()}><Download size={16} />CSV</Button>
        <Button variant="ghost" aria-label={t("analyticsWorkspace.refresh")} disabled={metrics.isFetching} onClick={() => void metrics.refetch()}><RefreshCw size={16} /></Button>
        <Button variant="ghost" aria-label={t("analyticsWorkspace.method")} onClick={() => setHelp(true)}><HelpCircle size={17} /></Button>
      </div>
    </div>
    {exportMutation.error || download.error ? <ErrorState error={exportMutation.error || download.error} /> : null}
    {receipt && !receipt.job ? <p role="status" className="text-sm text-platforma-subtle">{t("analyticsWorkspace.downloaded")}</p> : null}
    {currentJob ? <div role="status" className="flex flex-wrap items-center gap-3 rounded-control border border-platforma-border bg-surface-muted p-3 text-sm">
      <span>{t(`analyticsWorkspace.export.${currentJob.status}`)}</span>
      {currentJob.status === "succeeded" ? <Button variant="secondary" isLoading={download.isPending} onClick={() => download.mutate()}>{t("analyticsWorkspace.download")}</Button> : null}
    </div> : null}
    {job.error ? <ErrorState error={job.error} action={<Button variant="secondary" onClick={() => void job.refetch()}>{t("analyticsWorkspace.refresh")}</Button>} /> : null}
    {metrics.isPending ? <LoadingState scope="page" /> : metrics.error ? <ErrorState error={metrics.error} action={<Button variant="secondary" onClick={() => void metrics.refetch()}>{t("analyticsWorkspace.refresh")}</Button>} /> : metrics.data ? <>
      <div aria-busy={metrics.isFetching}>
        {active === "overview" ? <Overview data={metrics.data} /> : active === "sources" ? <SourcesTable data={metrics.data} /> : active === "services" ? <ServicesTable data={metrics.data} /> : active === "team" ? <TeamTable data={metrics.data} /> : <FinancialSummary report={metrics.data.financial} />}
      </div>
      <p className="text-xs text-platforma-subtle">{t("analyticsWorkspace.updated", { time: new Intl.DateTimeFormat(language, { dateStyle: "short", timeStyle: "short", timeZone: business.timezone }).format(new Date(metrics.data.generated_at)) })} · {metrics.data.period.timezone}</p>
    </> : null}
    <Dialog title={t("analyticsWorkspace.period")} open={periodOpen} onClose={() => setPeriodOpen(false)} size="sm">
      <div className="space-y-4">
        <DateRangePicker label={t("analyticsWorkspace.period")} value={draft} onChange={setDraft} today={today} />
        <div className="flex justify-end gap-2"><Button variant="ghost" onClick={() => setPeriodOpen(false)}>{t("common.cancel")}</Button><Button disabled={!isCalendarDate(draft.from) || !isCalendarDate(draft.to) || draft.from > draft.to} onClick={applyPeriod}>{t("crmFilters.apply")}</Button></div>
      </div>
    </Dialog>
    <Dialog title={t("analyticsWorkspace.method")} open={help} onClose={() => setHelp(false)} size="sm">
      <dl className="space-y-4 text-sm">{["period", "conversion", "noShow", "history", "money"].map(key => <div key={key}><dt className="font-bold">{t(`analyticsWorkspace.method.${key}`)}</dt><dd className="mt-1 leading-6 text-platforma-subtle">{t(`analyticsWorkspace.method.${key}Text`)}</dd></div>)}</dl>
    </Dialog>
  </div>;
}
