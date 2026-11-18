import { Link } from "react-router";

import type { WorkQueueResource, WorkQueuesResponse } from "../../api/workQueues";
import { Surface } from "../../components/ui/Card";
import { useI18n } from "../../lib/i18n";
import type { DashboardConnections } from "./OperationalDashboard";

type Props = {
  data: WorkQueuesResponse;
  access: Record<WorkQueueResource, boolean>;
  connections?: DashboardConnections;
};

export function DashboardAttention({ data, access, connections }: Props) {
  const { t, language } = useI18n();
  const canSee = (resource: WorkQueueResource) => access[resource] && data.available[resource];
  const groups = [
    { key: "pending_results", resource: "appointments", count: data.summary.pending_results,
      label: "records.pendingResult", at: data.queues.pending_results?.[0]?.end_at,
      href: "/app/appointments?attention=pending_result", action: "dashboard.reviewRecords" },
    { key: "overdue_tasks", resource: "tasks", count: data.summary.overdue_tasks,
      label: "dashboard.overdueTasks", at: data.queues.overdue_tasks[0]?.due_at,
      href: "/app/tasks?tab=overdue", action: "dashboard.reviewTasks" },
    { key: "appointment_confirmations", resource: "appointments", count: data.summary.appointment_confirmations,
      label: "dashboard.todayConfirmations", at: null,
      href: data.queues.appointment_confirmations[0]?.href, action: "dashboard.openNextConfirmation" },
    { key: "waiting_conversations", resource: "conversations", count: data.summary.waiting_conversations,
      label: "dashboard.waitingConversations", at: null,
      href: "/app/conversations?status=open", action: "dashboard.reviewConversations" },
  ] as const;
  const visibleGroups = groups.filter(group => canSee(group.resource) && group.count > 0);
  const failedConnections = connections?.health?.error || 0;
  const connectionsUnknown = connections && (connections.error || connections.loading || !connections.health);
  const linkClass = "platforma-focus-ring inline-flex min-h-11 items-center rounded-control text-sm font-semibold text-brand-700 hover:underline";

  return <Surface as="section" padding="lg" className={`min-w-0 ${canSee("appointments") ? "lg:col-start-2 lg:row-start-1" : ""}`} data-testid="dashboard-attention">
    <h2 className="text-base font-semibold text-platforma-text">{t("dashboard.attention")}</h2>
    <ul className="mt-2 divide-y divide-platforma-border">
      {visibleGroups.map(group => <li key={group.key} className="py-3" data-testid={`dashboard-group-${group.key}`}>
        <div className="flex items-baseline justify-between gap-3">
          <h3 className="text-sm font-medium text-platforma-text">{t(group.label)}</h3>
          <span className="text-xl font-semibold tabular-nums text-platforma-warning">{group.count}</span>
        </div>
        <p className="mt-1 text-xs text-platforma-subtle">{t(`dashboard.scope.${data.scope[group.resource] || "own"}`)}</p>
        {group.at ? <p className="mt-1 text-xs text-platforma-subtle">{t("dashboard.oldestSince", { at: new Intl.DateTimeFormat(language, {
          day: "numeric", month: language === "kk" ? "2-digit" : "short", year: "numeric", timeZone: data.timezone,
        }).format(new Date(group.at)) })}</p> : null}
        {group.href ? <Link to={group.href} className={linkClass}>{t(group.action)}</Link> : null}
      </li>)}
      {failedConnections > 0 ? <li className="py-3" data-testid="dashboard-group-connections">
        <div className="flex items-baseline justify-between gap-3">
          <h3 className="text-sm font-medium text-platforma-text">{t("dashboard.failedConnectors")}</h3>
          <span className="text-xl font-semibold tabular-nums text-platforma-warning">{failedConnections}</span>
        </div>
        <Link to="/app/integrations" className={linkClass}>{t("dashboard.reviewConnections")}</Link>
      </li> : null}
    </ul>
    {!visibleGroups.length && !failedConnections && !connectionsUnknown ? <p className="py-5 text-sm text-platforma-subtle">{t("dashboard.noPrioritiesTitle")}</p> : null}
    {connectionsUnknown ? <p role="status" className="mt-2 text-xs text-platforma-subtle">{t(connections.loading ? "common.loading" : "dashboard.connectionsUnavailable")}</p> : null}
  </Surface>;
}
