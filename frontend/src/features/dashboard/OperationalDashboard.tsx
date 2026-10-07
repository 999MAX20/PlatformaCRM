import { AlertTriangle, ArrowRight, CalendarCheck, CheckCircle2, Clock, MessageSquareText } from "lucide-react";
import { Link } from "react-router";

import type { WorkQueueResource, WorkQueuesResponse } from "../../api/workQueues";
import { normalizeAppError } from "../../api/appError";
import { Button } from "../../components/ui/Button";
import { Surface } from "../../components/ui/Card";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { useI18n } from "../../lib/i18n";
import { uniqueById } from "./dashboardUtils";

type Props = {
  data?: WorkQueuesResponse;
  error: unknown;
  loading: boolean;
  retry: () => void;
  access: Record<WorkQueueResource, boolean>;
  onMore: () => void;
};

export function OperationalDashboard({ data, error, loading, retry, access, onMore }: Props) {
  const { t, language } = useI18n();
  if (error) {
    const denied = ["permission", "authentication"].includes(normalizeAppError(error).category);
    return <div data-testid="dashboard-priority-error"><ErrorState error={error}
      message={t(denied ? "dashboard.operationsNoAccess" : "dashboard.priorityQueueError")}
      action={denied ? undefined : <Button variant="secondary" onClick={retry}>{t("common.retry")}</Button>}
    /></div>;
  }
  if (loading || !data) return <LoadingState />;

  const canSee = (resource: WorkQueueResource) => access[resource] && data.available[resource];
  const scopeLabel = (resource: WorkQueueResource) => t(`dashboard.scope.${data.scope[resource] || "own"}`);
  const formatTime = (value: string) => new Intl.DateTimeFormat(language, {
    day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: data.timezone,
  }).format(new Date(value));
  const todayLabel = new Intl.DateTimeFormat(language, { day: "numeric", month: "long", timeZone: data.timezone }).format(new Date(data.generated_at));
  const calendarHref = `/app/calendar?date=${data.day}&view=day`;
  const conversation = data.attention.find((item) => item.type === "conversation")
    || data.queues.handoff_conversations[0] || data.queues.unread_conversations[0];
  const metrics = [
    { key: "today_appointments", resource: "appointments", label: "dashboard.todayBookings", icon: CalendarCheck, href: calendarHref, hint: `${todayLabel} · ${scopeLabel("appointments")}` },
    { key: "today_confirmations", resource: "appointments", label: "dashboard.todayConfirmations", icon: Clock, href: `${calendarHref}&status=created`, hint: `${todayLabel} · ${scopeLabel("appointments")}` },
    { key: "waiting_conversations", resource: "conversations", label: "dashboard.waitingConversations", icon: MessageSquareText, href: conversation?.href || "/app/conversations?status=open&unread=true", hint: scopeLabel("conversations") },
    { key: "overdue_tasks", resource: "tasks", label: "dashboard.overdueTasks", icon: AlertTriangle, href: "/app/tasks?tab=overdue", hint: scopeLabel("tasks") },
  ] as const;
  const resourceByType: Record<string, WorkQueueResource> = { task: "tasks", lead: "leads", deal: "deals", appointment: "appointments", conversation: "conversations" };
  const items = data.attention.filter((item) => canSee(resourceByType[item.type]));
  const hasAccess = Object.keys(access).some((key) => canSee(key as WorkQueueResource));

  return <div className="space-y-4" data-testid="dashboard-operations">
    <div className="flex flex-wrap items-baseline justify-between gap-2">
      <h2 className="text-lg font-semibold text-platforma-text">{t("common.today")}, {todayLabel}</h2>
      <p className="text-xs text-platforma-subtle">{data.timezone} · {t("dashboard.asOf", { at: formatTime(data.generated_at) })}</p>
    </div>
    <section className="grid grid-cols-2 gap-3 xl:grid-cols-4" aria-label={t("dashboard.operationalMetrics")}>
      {metrics.filter((metric) => canSee(metric.resource)).map((metric) => <Surface key={metric.key} as={Link} to={metric.href}
        interactive padding="md" className="platforma-focus-ring min-w-0" data-testid={`dashboard-metric-${metric.key}`}>
        <div className="flex items-start justify-between gap-2"><p className="text-sm font-medium text-platforma-subtle">{t(metric.label)}</p><metric.icon size={18} aria-hidden="true" className="shrink-0 text-brand-700" /></div>
        <p className="my-2 text-3xl font-semibold tabular-nums text-platforma-text">{data.summary[metric.key]}</p>
        <p className="text-xs text-platforma-subtle">{metric.hint}</p>
      </Surface>)}
    </section>
    {!hasAccess ? <p role="status" className="text-sm text-platforma-subtle">{t("dashboard.operationsNoAccess")}</p> :
      <div className={`grid min-w-0 items-start gap-4 ${canSee("appointments") ? "lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]" : "grid-cols-1"}`}>
        <Surface as="section" padding="lg" className="min-w-0" data-testid="dashboard-attention">
          <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-base font-semibold text-platforma-text">{t("dashboard.attention")}</h2>
            <span className="text-xs text-platforma-subtle">{t("dashboard.attentionOrder")}</span>
          </div>
          {items.length ? <ul className="divide-y divide-platforma-border">
            {items.map((item) => <li key={`${item.type}:${item.id}`}>
              <Link to={item.href} className="platforma-focus-ring flex min-h-20 items-center gap-3 rounded-control py-3 hover:bg-surface-hover" data-testid="dashboard-attention-item">
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-platforma-warning">{t(`dashboard.reason.${item.attention_reason}`)}</p>
                  <p className="mt-1 break-words text-sm font-semibold text-platforma-text">{item.title}</p>
                  {item.attention_at ? <p className="mt-1 text-xs text-platforma-subtle">{item.type === "conversation"
                    ? t("dashboard.waitingMinutes", { count: Math.max(0, Math.floor((Date.parse(data.generated_at) - Date.parse(item.attention_at)) / 60000)) })
                    : formatTime(item.attention_at)}</p> : null}
                </div>
                <span className="flex shrink-0 items-center gap-1 text-xs font-semibold text-brand-700">{t("common.open")}<ArrowRight size={15} aria-hidden="true" /></span>
              </Link>
            </li>)}
          </ul> : <div className="flex items-center gap-3 py-8 text-sm text-platforma-subtle"><CheckCircle2 size={22} aria-hidden="true" className="shrink-0 text-brand-700" />{t("dashboard.noPrioritiesTitle")}</div>}
          {data.summary.total_attention > items.length ? <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-platforma-border pt-3">
            <p className="text-xs text-platforma-subtle">{t("dashboard.previewCount", { shown: items.length, total: data.summary.total_attention })}</p>
            {data.limit < 50 ? <Button size="sm" variant="secondary" onClick={onMore}>{t("dashboard.showMore")}</Button> : null}
          </div> : null}
        </Surface>
        {canSee("appointments") ? <Surface as="section" padding="lg" className="min-w-0" data-testid="dashboard-upcoming">
          <h2 className="text-base font-semibold text-platforma-text">{t("dashboard.upcomingAppointments")}</h2>
          <p className="mt-1 text-xs text-platforma-subtle">{t("dashboard.next24Hours")}</p>
          {data.queues.upcoming_appointments.length ? <ul className="mt-2 divide-y divide-platforma-border">
            {uniqueById(data.queues.upcoming_appointments).slice(0, 4).map((appointment) => <li key={appointment.id} data-testid="dashboard-appointment-row" data-appointment-id={appointment.id}>
              <Link to={appointment.href} className="platforma-focus-ring block rounded-control py-3 hover:bg-surface-hover">
                <p className="text-xs font-semibold tabular-nums text-brand-700">{formatTime(appointment.start_at)}</p>
                <p className="mt-1 break-words text-sm font-semibold text-platforma-text">{appointment.title}</p>
                {appointment.resource_name ? <p className="mt-1 text-xs text-platforma-subtle">{appointment.resource_name}</p> : null}
                <div className="mt-2"><StatusBadge status={appointment.status} size="sm" /></div>
              </Link>
            </li>)}
          </ul> : <p className="py-8 text-sm text-platforma-subtle">{t("dashboard.noUpcomingAppointments")}</p>}
          <Link to={calendarHref} className="platforma-focus-ring mt-3 inline-flex min-h-9 items-center gap-2 rounded-control text-sm font-semibold text-brand-700">{t("dashboard.openCalendar")}<ArrowRight size={15} aria-hidden="true" /></Link>
        </Surface> : null}
      </div>}
  </div>;
}
