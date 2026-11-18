import { Link } from "react-router";
import type { ReactNode } from "react";

import type { WorkQueueResource, WorkQueuesResponse } from "../../api/workQueues";
import { normalizeAppError } from "../../api/appError";
import { Button } from "../../components/ui/Button";
import { Surface } from "../../components/ui/Card";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { useI18n } from "../../lib/i18n";
import { formatDateTime } from "../../lib/format";
import type { OwnerDashboardMetrics } from "../../types";
import { uniqueById } from "./dashboardUtils";
import { DashboardAttention } from "./DashboardAttention";

export type DashboardConnections = {
  health?: OwnerDashboardMetrics["connector_health"];
  error: unknown;
  loading: boolean;
};

type Props = {
  data?: WorkQueuesResponse;
  error: unknown;
  loading: boolean;
  refreshing: boolean;
  retry: () => void;
  access: Record<WorkQueueResource, boolean>;
  canCreateAppointment: boolean;
  connections?: DashboardConnections;
  financial?: ReactNode;
};

export function OperationalDashboard({ data, error, loading, refreshing, retry, access, canCreateAppointment, connections, financial }: Props) {
  const { t, language } = useI18n();
  const denied = Boolean(error && ["permission", "authentication"].includes(normalizeAppError(error).category));
  if (error && (!data || denied)) return <><div data-testid="dashboard-priority-error"><ErrorState error={error}
    message={t(denied ? "dashboard.operationsNoAccess" : "dashboard.priorityQueueError")}
    action={denied ? undefined : <Button variant="secondary" onClick={retry}>{t("common.retry")}</Button>}
  /></div>{financial}</>;
  if (loading || !data) return <LoadingState />;

  const canSee = (resource: WorkQueueResource) => access[resource] && data.available[resource];
  const scopeLabel = (resource: WorkQueueResource) => t(`dashboard.scope.${data.scope[resource] || "own"}`);
  const formatTime = (value: string) => formatDateTime(value, data.timezone, false, language);
  const todayLabel = new Intl.DateTimeFormat(language, { day: "numeric", month: language === "kk" ? "2-digit" : "long", timeZone: data.timezone }).format(new Date(data.generated_at));
  const metrics = [
    { key: "today_appointments", resource: "appointments", label: "dashboard.todayBookings", href: `/app/appointments?from=${data.day}`, hint: `${todayLabel} · ${scopeLabel("appointments")}` },
    { key: "today_confirmations", resource: "appointments", label: "dashboard.todayConfirmations", href: `/app/appointments?from=${data.day}&confirmed=false&workflow=planned`, hint: `${todayLabel} · ${scopeLabel("appointments")}` },
    { key: "waiting_conversations", resource: "conversations", label: "dashboard.waitingConversations", href: "/app/conversations?status=open", hint: scopeLabel("conversations") },
    { key: "overdue_tasks", resource: "tasks", label: "dashboard.overdueTasks", href: "/app/tasks?tab=overdue", hint: scopeLabel("tasks") },
  ] as const;
  const visibleMetrics = metrics.filter(metric => canSee(metric.resource));
  const upcoming = uniqueById(data.queues.upcoming_appointments).slice(0, 5);
  const linkClass = "platforma-focus-ring inline-flex min-h-11 items-center rounded-control text-sm font-semibold text-brand-700 hover:underline";

  return <div className="space-y-4" data-testid="dashboard-operations">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 className="text-xl font-semibold text-platforma-text">{t("dashboard.periodToday")}, {todayLabel}</h2>
        <p className="mt-1 text-xs text-platforma-subtle">{t("dashboard.asOf", { at: formatTime(data.generated_at) })}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="secondary" className="min-h-11" onClick={retry} disabled={refreshing}>{t("common.refresh")}</Button>
        {canSee("appointments") && canCreateAppointment ? <Link to="/app/appointments?create=1" className="platforma-focus-ring inline-flex min-h-11 items-center justify-center rounded-control bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600 active:bg-brand-700">{t("appointments.create")}</Link> : null}
      </div>
    </div>
    {error ? <div role="alert" className="text-sm text-platforma-warning">{t("dashboard.refreshFailed")}</div> : null}
    {visibleMetrics.length ? <Surface as="section" padding="none" aria-label={t("dashboard.operationalMetrics")}>
      <div className={`grid ${visibleMetrics.length === 1 ? "grid-cols-1" : "grid-cols-2"} ${visibleMetrics.length === 4 ? "xl:grid-cols-4" : visibleMetrics.length === 3 ? "xl:grid-cols-3" : ""}`}>
        {visibleMetrics.map((metric, index) => <Link key={metric.key} to={metric.href}
          className={`platforma-focus-ring min-w-0 border-platforma-border px-4 py-3 hover:bg-surface-hover ${index % 2 ? "border-l" : ""} ${index > 1 ? "border-t xl:border-t-0" : ""} ${index > 0 ? "xl:border-l" : ""} ${visibleMetrics.length === 3 && index === 2 ? "col-span-2 xl:col-span-1" : ""}`} data-testid={`dashboard-metric-${metric.key}`}>
          <p className="min-h-10 text-sm text-platforma-subtle xl:min-h-0">{t(metric.label)}</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-platforma-text">{data.summary[metric.key]}</p>
          <p className="mt-1 text-xs text-platforma-subtle">{metric.hint}</p>
        </Link>)}
      </div>
    </Surface> : <p role="status" className="text-sm text-platforma-subtle">{t("dashboard.operationsNoAccess")}</p>}
    <div className={`grid min-w-0 items-start gap-4 ${canSee("appointments") ? "lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]" : "grid-cols-1"}`}>
      {visibleMetrics.length || connections ? <DashboardAttention data={data} access={access} connections={connections} /> : null}
      <div className={`min-w-0 space-y-4 ${canSee("appointments") ? "lg:col-start-1 lg:row-start-1" : ""}`}>
      {canSee("appointments") ? <Surface as="section" padding="lg" className="min-w-0" data-testid="dashboard-upcoming">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-base font-semibold text-platforma-text">{t("dashboard.upcomingAppointments")}</h2>
          <p className="text-xs text-platforma-subtle">{t("dashboard.next24Hours")}</p>
        </div>
        {upcoming.length ? <ul className="mt-3 divide-y divide-platforma-border">
          {upcoming.map(appointment => <li key={appointment.id} data-testid="dashboard-appointment-row" data-appointment-id={appointment.id}>
            <Link to={appointment.href} className="platforma-focus-ring grid min-w-0 gap-2 rounded-control py-4 hover:bg-surface-hover sm:grid-cols-[7rem_minmax(0,1fr)_auto] sm:items-center">
              <time dateTime={appointment.start_at} className="text-sm font-medium tabular-nums text-platforma-text">{formatTime(appointment.start_at)}</time>
              <div className="min-w-0">
                <p className="break-words text-sm font-semibold text-platforma-text">{appointment.title}</p>
                {appointment.resource_name ? <p className="mt-1 break-words text-xs text-platforma-subtle">{appointment.resource_name}</p> : null}
              </div>
              <div className="justify-self-start sm:justify-self-end"><StatusBadge status={appointment.status} size="sm" /></div>
            </Link>
          </li>)}
        </ul> : <p className="py-8 text-sm text-platforma-subtle">{t("dashboard.noUpcomingAppointments")}</p>}
        {data.summary.upcoming_appointments > upcoming.length ? <p className="mt-3 text-xs text-platforma-subtle">{t("dashboard.previewCount", { shown: upcoming.length, total: data.summary.upcoming_appointments })}</p> : null}
        <Link to={`/app/calendar?date=${data.day}&view=day`} className={linkClass}>{t("dashboard.openCalendar")}</Link>
      </Surface> : null}
      {financial}
      </div>
    </div>
  </div>;
}
