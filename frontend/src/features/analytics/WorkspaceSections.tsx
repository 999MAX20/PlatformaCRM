import { ArrowUpRight } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { ForbiddenState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { RecordMetric, type ReportProps } from "./Comparison";
import { includePreviousGroups } from "./comparisonValues";

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

function Breakdown({ title, rows, unavailable }: { title: string; rows: { label: string; value: number; danger?: boolean; content?: ReactNode }[]; unavailable?: boolean }) {
  const { t } = useI18n();
  const maximum = Math.max(1, ...rows.map(row => row.value));
  return <Card><CardHeader><h2 className="text-base font-bold">{title}</h2></CardHeader><CardBody>
    {unavailable ? <p className="text-sm text-platforma-subtle">{t("analyticsWorkspace.unavailable")}</p>
      : rows.every(row => !row.value && !row.content) ? <p className="text-sm text-platforma-subtle">{t("analyticsWorkspace.empty")}</p>
      : <dl className="space-y-4">{rows.map(row => <div key={row.label} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-2 text-[13px] sm:grid-cols-[minmax(120px,1fr)_1fr_auto]">
        <dt>{row.label}</dt><div aria-hidden="true" className="col-start-1 row-start-2 h-2 overflow-hidden rounded-full bg-surface-muted sm:col-start-auto sm:row-start-auto"><div className={`h-full rounded-full ${row.danger ? "bg-platforma-danger" : "bg-brand-500"}`} style={{ width: `${row.value / maximum * 100}%` }} /></div>
        <dd className="text-right font-semibold tabular-nums">{row.content ?? <MetricValue value={row.value} />}</dd></div>)}</dl>}
  </CardBody></Card>;
}

export function SourcesTable({ data, onRecords }: ReportProps) {
  const previous = data.comparison?.available ? data.comparison.record_sources : [];
  const rows = includePreviousGroups(data.record_sources, previous, row => row.source, row => ({ ...row, total: 0, completed: 0, cancelled: 0, no_show: 0 }));
  const { t } = useI18n();
  if (!data.availability.appointments) return <ForbiddenState />;
  return <ReportTable title={t("records.sources")}
    columns={[t("analyticsWorkspace.source"), t("appointments.title"), t("records.completed"), t("records.cancelled"), t("records.no_show")]}
    rows={rows.map(row => [t(`appointment.source.${row.source}`), ...(["total", "completed", "cancelled", "no_show"] as const).map(metric => <RecordMetric data={data} onRecords={onRecords} label={`${t(`appointment.source.${row.source}`)} · ${t(metric === "total" ? "appointments.title" : `records.${metric}`)}`} value={row[metric]} previous={previous.find(old => old.source === row.source)?.[metric] ?? 0} filters={{ source: row.source, metric }} />)])} />;
}

export function ServicesTable({ data, onRecords }: ReportProps) {
  const previous = data.comparison?.available ? data.comparison.services : [];
  const rows = includePreviousGroups(data.services, previous, row => row.service_id, row => ({ ...row, total: 0, completed: 0, no_show: 0 }));
  const { t } = useI18n();
  if (!data.availability.appointments) return <ForbiddenState />;
  return <ReportTable title={t("analyticsWorkspace.services")}
    columns={[t("analyticsWorkspace.service"), t("nav.appointments"), t("analyticsWorkspace.completed"), t("analytics.noShow")]}
    rows={rows.map(row => [row.service__name, ...(["total", "completed", "no_show"] as const).map(metric => <RecordMetric data={data} onRecords={onRecords} label={`${row.service__name} · ${t(metric === "total" ? "appointments.title" : `records.${metric}`)}`} value={row[metric]} previous={previous.find(old => old.service_id === row.service_id)?.[metric] ?? 0} filters={{ service: row.service_id, metric }} />)])} />;
}

export function TeamTable({ data, onRecords }: ReportProps) {
  const previous = data.comparison?.available ? data.comparison.team : [];
  const { t } = useI18n();
  if (!data.team.available) return <ForbiddenState title={t("analytics.teamHidden")} />;
  return <div className="space-y-4">
    <p className="text-sm text-platforma-subtle">{t(`analyticsWorkspace.scope.${data.team.scope}`)} {t("analyticsWorkspace.teamCoverage")}</p>
    <ReportTable title={t("analytics.employees")}
    columns={[t("appointment.responsible"), t("appointments.title"), t("records.completed")]}
    rows={data.team.rows.map(row => [row.name, ...(["appointments", "completed_appointments"] as const).map(key => <RecordMetric data={data} onRecords={onRecords} label={`${row.name} · ${t(key === "appointments" ? "appointments.title" : "records.completed")}`} value={row[key]} previous={previous.find(old => old.id === row.id)?.[key] ?? null} filters={{ responsible_user: row.id, metric: key === "appointments" ? "total" : "completed" }} />)])} />
    <ReportTable title={t("analyticsWorkspace.workloadNow")}
      columns={[t("analyticsWorkspace.employee"), t("dashboard.openTasks"), t("analytics.overdueTasks"), t("analytics.unansweredConversations")]}
      rows={data.team.rows.map(row => [row.name, <MetricValue value={row.open_tasks} />, <MetricValue value={row.overdue_tasks} />, <MetricValue value={row.unanswered} />])} />
  </div>;
}

export function Overview({ data, onRecords }: ReportProps) {
  const previous = data.comparison?.available ? data.comparison.appointments : null;
  const oldStatuses = previous?.by_status || {};
  const { t } = useI18n();
  const stats = [
    { label: t("appointments.title"), value: data.appointments.total, previous: previous?.total ?? null, metric: "total" as const },
    { label: t("records.completionRate"), value: data.appointments.completion_rate, previous: previous?.completion_rate ?? null, metric: "completed" as const, percent: true },
    { label: t("records.completed"), value: data.appointments.completed, previous: previous?.completed ?? null, metric: "completed" as const },
    { label: t("analytics.noShowRate"), value: data.appointments.no_show_rate, previous: previous?.no_show_rate ?? null, metric: "no_show" as const, percent: true },
  ];
  const statuses = data.appointments.by_status || {};
  const appointmentRows = [
    { label: t("analyticsWorkspace.completed"), value: statuses.completed || 0, previous: oldStatuses.completed || 0, metric: "completed" as const },
    { label: t("analyticsWorkspace.planned"), value: (statuses.created || 0) + (statuses.confirmed || 0) + (statuses.rescheduled || 0), previous: (oldStatuses.created || 0) + (oldStatuses.confirmed || 0) + (oldStatuses.rescheduled || 0), metric: "planned" as const },
    { label: t("analyticsWorkspace.cancelled"), value: statuses.cancelled || 0, previous: oldStatuses.cancelled || 0, metric: "cancelled" as const },
    { label: t("analytics.noShow"), value: statuses.no_show || 0, previous: oldStatuses.no_show || 0, metric: "no_show" as const, danger: true },
  ];
  const attention = [
    { label: t("analytics.overdueTasks"), value: data.current.overdue_tasks, href: "/app/tasks?tab=all&bucket=overdue" },
    { label: t("analytics.unansweredConversations"), value: data.current.unanswered, href: "/app/conversations?status=open&unanswered=true" },
    { label: t("records.pendingResult"), value: data.current.pending_records, href: "/app/appointments?attention=pending_result" },
  ];
  return <div className="space-y-4">
    <Card><dl className="grid grid-cols-2 divide-platforma-border lg:grid-cols-4">{stats.map((stat, index) => <div key={stat.label} className={`px-4 py-4 ${index ? "lg:border-l" : ""}`}><dt className="text-xs font-semibold text-platforma-subtle">{stat.label}</dt><dd className="mt-2 text-[26px] font-bold leading-8 tabular-nums"><RecordMetric data={data} onRecords={onRecords} label={stat.label} value={stat.value} previous={stat.previous} percent={stat.percent} filters={{ metric: stat.metric }} /></dd></div>)}</dl></Card>
    <div className="grid gap-4 lg:grid-cols-2">
      <Breakdown title={t("nav.appointments")} unavailable={!data.availability.appointments} rows={appointmentRows.map(row => ({ ...row, content: <RecordMetric data={data} onRecords={onRecords} label={row.label} value={row.value} previous={row.previous} filters={{ metric: row.metric }} /> }))} />
      <SourcesTable data={data} onRecords={onRecords} />
    </div>
    <Card><CardHeader><h2 className="text-base font-bold">{t("analyticsWorkspace.attentionNow")}</h2></CardHeader><ul className="divide-y divide-platforma-border">
      {attention.filter(item => item.value !== null).map(item => <li key={item.href}><Link to={item.href} className="flex min-h-12 items-center gap-3 px-4 py-3 text-sm hover:bg-surface-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"><span className="flex-1">{item.label}</span><span className="font-semibold tabular-nums"><MetricValue value={item.value} /></span><ArrowUpRight size={16} aria-hidden="true" /></Link></li>)}
    </ul></Card>
  </div>;
}
