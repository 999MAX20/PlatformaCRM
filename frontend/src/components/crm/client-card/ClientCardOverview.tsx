import { useQuery } from "@tanstack/react-query";
import { CalendarDays, ExternalLink } from "lucide-react";
import { Link } from "react-router";
import { appointmentsApi } from "../../../api/appointments";
import { useAuth } from "../../../features/auth/AuthProvider";
import { useActiveBusiness } from "../../../hooks/useBusiness";
import { dateInTimeZone, formatDateTime } from "../../../lib/format";
import { useI18n } from "../../../lib/i18n";
import { hasPermission } from "../../../lib/permissions";
import type { CrmCardPayload } from "../../../types";
import { Button } from "../../ui/Button";
import { ErrorState, LoadingState } from "../../ui/StateViews";
import { StatusBadge } from "../../ui/StatusBadge";
import { formatTimelineEventText } from "../drawers/timelineHelpers";

export function ClientCardOverview({ data, onHistory, onOpenAppointment }: { data: CrmCardPayload; onHistory: () => void; onOpenAppointment?: (id: number) => void }) {
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const { t, language } = useI18n();
  const zone = business?.timezone || "UTC";
  const client = data.client!;
  const canView = hasPermission(user, client.business, "appointments", "view");
  const next = useQuery({
    queryKey: ["appointments", "client-card-next", client.business, user?.id, client.id],
    enabled: canView,
    staleTime: 0,
    refetchInterval: 60_000,
    queryFn: async () => {
      const now = new Date();
      // Workspace sorts before pagination; the limited crm-card relations cannot prove nearest.
      for (let page = 1; ; page++) {
        const result = await appointmentsApi.workspace({ business: client.business, client: client.id,
          workflow: "planned", ordering: "start_at", start_from: dateInTimeZone(now.toISOString(), zone), page, page_size: 25 });
        const appointment = result.results.find(item => !item.is_archived && new Date(item.end_at).getTime() > now.getTime());
        if (appointment) return appointment;
        if (!result.next) return null;
      }
    },
  });
  return <div className="space-y-6">
    {canView ? <section aria-labelledby="client-card-next-title">
      <h3 id="client-card-next-title" className="mb-3 text-sm font-semibold text-platforma-subtle">{t("clients.card.nextAppointment")}</h3>
      {next.isPending ? <LoadingState /> : next.error ? <ErrorState error={next.error} action={<Button variant="secondary" onClick={() => void next.refetch()}>{t("common.retry")}</Button>} /> : next.data ? <div className="rounded-card bg-brand-50 p-4" data-testid="client-card-next">
        <div className="flex flex-wrap items-center gap-4">
          <p className="flex items-center gap-2 text-lg font-semibold"><CalendarDays size={20} className="shrink-0 text-brand-700" />{formatDateTime(next.data.start_at, zone, true, language)}</p>
          <div className="min-w-0 flex-[1_1_144px]"><p className="break-words text-sm font-medium">{next.data.service_name}</p><p className="text-xs text-platforma-subtle">{t("appointment.service")}</p></div>
          {next.data.resource_name ? <div className="min-w-0 flex-[1_1_144px]"><p className="break-words text-sm font-medium">{next.data.resource_name}</p><p className="text-xs text-platforma-subtle">{t("appointment.resource")}</p></div> : null}
          <StatusBadge status={next.data.status} />
        </div>
        {onOpenAppointment ? <Button variant="ghost" className="mt-3" onClick={() => onOpenAppointment(next.data!.id)}>{t("plans.openAppointment")}</Button> : <Link className="platforma-focus-ring mt-3 inline-flex min-h-10 items-center gap-2 rounded-control text-sm font-semibold text-brand-700" to={`/app/appointments/${next.data.id}`}><ExternalLink size={16} />{t("plans.openAppointment")}</Link>}
      </div> : <p className="rounded-card border border-platforma-border p-4 text-sm text-platforma-subtle">{t("clients.card.noUpcoming")}</p>}
    </section> : null}
    <section>
      <div className="mb-4 flex items-center justify-between gap-3"><h3 className="text-lg font-semibold">{t("clients.card.activity")}</h3><Button variant="ghost" size="sm" onClick={onHistory}>{t("crmCard.timeline")}</Button></div>
      {data.timeline.length ? <ol className="ml-2 border-l border-platforma-border">
        {data.timeline.slice(0, 4).map(event => <li key={event.id} className="relative pb-5 pl-6 last:pb-0">
          <span aria-hidden className="absolute -left-[5px] top-1 h-[9px] w-[9px] rounded-full border-2 border-brand-700 bg-surface-card" />
          <time className="text-xs text-platforma-subtle">{formatDateTime(event.created_at, zone, true, language)}</time>
          <p className="mt-1 whitespace-pre-wrap break-words text-sm leading-6">{event.event_type === "visit_plan_changed" ? formatTimelineEventText(event, t) : event.text || event.event_type}</p>
        </li>)}
      </ol> : <p className="text-sm text-platforma-subtle">{t("crmCard.emptyTimelineText")}</p>}
    </section>
  </div>;
}
