import { ArrowUpRight } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { ForbiddenState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import type { AnalyticsWorkspace } from "../../types/analyticsWorkspace";

export function MetricValue({ value, percent = false }: { value: number | null; percent?: boolean }) {
  const { language } = useI18n();
  return <>{value === null ? "—" : `${new Intl.NumberFormat(language).format(value)}${percent ? "%" : ""}`}</>;
}

export function ReportTable({ title, columns, rows }: { title: string; columns: string[]; rows: ReactNode[][] }) {
  const { t } = useI18n();
  return <Card className="min-w-0 overflow-hidden"><CardHeader><h2 className="text-base font-bold">{title}</h2></CardHeader>
    {rows.length ? <div className="overflow-x-auto" tabIndex={0} role="region" aria-label={title}>
      <table className="w-full text-left text-[13px] tabular-nums"><caption className="sr-only">{title}</caption>
        <thead className="bg-surface-muted text-xs text-platforma-subtle"><tr>{columns.map((column, i) => <th key={i} scope="col" className={`whitespace-nowrap px-4 py-3 font-semibold ${i ? "text-right" : "text-left"}`}>{column}</th>)}</tr></thead>
        <tbody className="divide-y divide-platforma-border">{rows.map((row, i) => <tr key={i} className="hover:bg-surface-hover">{row.map((cell, j) => j === 0
          ? <th key={j} scope="row" className="min-w-36 px-4 py-3 font-semibold">{cell}</th>
          : <td key={j} className="whitespace-nowrap px-4 py-3 text-right">{cell}</td>)}</tr>)}</tbody>
      </table></div> : <p className="p-4 text-sm text-platforma-subtle">{t("analyticsWorkspace.empty")}</p>}
  </Card>;
}

function Breakdown({ title, rows, unavailable }: { title: string; rows: { label: string; value: number; danger?: boolean }[]; unavailable?: boolean }) {
  const { t } = useI18n();
  const maximum = Math.max(1, ...rows.map(row => row.value));
  return <Card><CardHeader><h2 className="text-base font-bold">{title}</h2></CardHeader><CardBody>
    {unavailable ? <p className="text-sm text-platforma-subtle">{t("analyticsWorkspace.unavailable")}</p>
      : rows.every(row => !row.value) ? <p className="text-sm text-platforma-subtle">{t("analyticsWorkspace.empty")}</p>
      : <dl className="space-y-4">{rows.map(row => <div key={row.label} className="grid grid-cols-[minmax(90px,1fr)_2fr_32px] items-center gap-3 text-[13px]">
        <dt className="break-words">{row.label}</dt><div aria-hidden="true" className="h-2 overflow-hidden rounded-full bg-surface-muted"><div className={`h-full rounded-full ${row.danger ? "bg-platforma-danger" : "bg-brand-500"}`} style={{ width: `${row.value / maximum * 100}%` }} /></div>
        <dd className="text-right font-semibold tabular-nums"><MetricValue value={row.value} /></dd></div>)}</dl>}
  </CardBody></Card>;
}

export function SourcesTable({ data }: { data: AnalyticsWorkspace }) {
  const { t } = useI18n();
  if (!data.availability.leads) return <ForbiddenState />;
  return <ReportTable title={t("analytics.leadSources")}
    columns={[t("analyticsWorkspace.source"), t("nav.leads"), t("analyticsWorkspace.converted"), t("dashboard.conversion")]}
    rows={data.sources.map(row => {
      const key = `analytics.source.${row.source}`;
      return [t(key) === key ? row.source : t(key), <MetricValue value={row.leads} />, <MetricValue value={row.converted} />, <MetricValue value={row.conversion_rate} percent />];
    })} />;
}

export function ServicesTable({ data }: { data: AnalyticsWorkspace }) {
  const { t } = useI18n();
  if (!data.availability.appointments) return <ForbiddenState />;
  return <ReportTable title={t("analyticsWorkspace.services")}
    columns={[t("analyticsWorkspace.service"), t("nav.appointments"), t("analyticsWorkspace.completed"), t("analytics.noShow")]}
    rows={data.services.map(row => [row.service__name, <MetricValue value={row.total} />, <MetricValue value={row.completed} />, <MetricValue value={row.no_show} />])} />;
}

export function TeamTable({ data }: { data: AnalyticsWorkspace }) {
  const { t } = useI18n();
  if (!data.team.available) return <ForbiddenState title={t("analytics.teamHidden")} />;
  return <div className="space-y-4"><ReportTable title={t("analytics.employees")}
    columns={[t("analyticsWorkspace.employee"), t("nav.leads"), t("analyticsWorkspace.converted"), t("dashboard.conversion"), t("analyticsWorkspace.won"), t("analyticsWorkspace.lost")]}
    rows={data.team.rows.map(row => [row.name, <MetricValue value={row.leads} />, <MetricValue value={row.converted} />, <MetricValue value={row.conversion_rate} percent />, <MetricValue value={row.won} />, <MetricValue value={row.lost} />])} />
    <ReportTable title={t("analyticsWorkspace.workloadNow")}
      columns={[t("analyticsWorkspace.employee"), t("dashboard.openTasks"), t("analytics.overdueTasks"), t("analytics.unansweredConversations")]}
      rows={data.team.rows.map(row => [row.name, <MetricValue value={row.open_tasks} />, <MetricValue value={row.overdue_tasks} />, <MetricValue value={row.unanswered} />])} />
  </div>;
}

export function Overview({ data }: { data: AnalyticsWorkspace }) {
  const { t } = useI18n();
  const stats = [
    { label: t("nav.leads"), value: data.leads.total },
    { label: t("analytics.leadToDeal"), value: data.leads.conversion_rate, percent: true },
    { label: t("analyticsWorkspace.wonDeals"), value: data.deals.won },
    { label: t("analytics.noShowRate"), value: data.appointments.no_show_rate, percent: true },
  ];
  const statuses = data.appointments.by_status || {};
  const appointmentRows = [
    { label: t("analyticsWorkspace.completed"), value: statuses.completed || 0 },
    { label: t("analyticsWorkspace.planned"), value: (statuses.created || 0) + (statuses.confirmed || 0) },
    { label: t("analyticsWorkspace.cancelled"), value: statuses.cancelled || 0 },
    { label: t("analytics.noShow"), value: statuses.no_show || 0, danger: true },
    { label: t("appointment.statusRescheduled"), value: statuses.rescheduled || 0 },
  ];
  const attention = [
    { label: t("analytics.overdueTasks"), value: data.current.overdue_tasks, href: "/app/tasks?tab=all&bucket=overdue" },
    { label: t("analytics.unansweredConversations"), value: data.current.unanswered, href: "/app/conversations?status=open" },
    { label: t("dashboard.newLeads"), value: data.current.new_leads, href: "/app/leads?quick=new" },
  ];
  return <div className="space-y-4">
    <Card><dl className="grid grid-cols-2 divide-platforma-border lg:grid-cols-4">{stats.map((stat, index) => <div key={stat.label} className={`px-4 py-4 ${index ? "lg:border-l" : ""}`}><dt className="text-xs font-semibold text-platforma-subtle">{stat.label}</dt><dd className="mt-2 text-[26px] font-bold leading-8 tabular-nums"><MetricValue value={stat.value} percent={stat.percent} /></dd></div>)}</dl></Card>
    <div className="grid gap-4 lg:grid-cols-2">
      <Breakdown title={t("analyticsWorkspace.dealResults")} unavailable={!data.availability.deals} rows={[
        { label: t("analyticsWorkspace.won"), value: data.deals.won || 0 }, { label: t("analyticsWorkspace.lost"), value: data.deals.lost || 0, danger: true },
      ]} />
      <Breakdown title={t("nav.appointments")} unavailable={!data.availability.appointments} rows={appointmentRows} />
    </div>
    <SourcesTable data={data} />
    <Card><CardHeader><h2 className="text-base font-bold">{t("analyticsWorkspace.attentionNow")}</h2></CardHeader><ul className="divide-y divide-platforma-border">
      {attention.filter(item => item.value !== null).map(item => <li key={item.href}><Link to={item.href} className="flex min-h-12 items-center gap-3 px-4 py-3 text-sm hover:bg-surface-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"><span className="flex-1">{item.label}</span><span className="font-semibold tabular-nums"><MetricValue value={item.value} /></span><ArrowUpRight size={16} aria-hidden="true" /></Link></li>)}
      {data.deals.open_now !== null ? <li className="flex items-center justify-between px-4 py-3 text-sm"><span>{t("analyticsWorkspace.openNow")}</span><span className="font-semibold tabular-nums"><MetricValue value={data.deals.open_now} /></span></li> : null}
    </ul></Card>
  </div>;
}
