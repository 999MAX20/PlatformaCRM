import { formatDateTime } from "../../../lib/format";
import { useI18n } from "../../../lib/i18n";
import type { CrmCardPayload } from "../../../types";
import { StatusBadge } from "../../ui/StatusBadge";
import { drawerSurfaceClass, EmptyBlock } from "./shared";

export function EntityAppointmentsPanel({ data }: { data: CrmCardPayload }) {
  const { t } = useI18n();
  return (
    <div className="space-y-3">
      {data.appointments.map((appointment) => (
        <div key={appointment.id} className={drawerSurfaceClass}>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate font-bold text-platforma-ink">{appointment.service_name || t("nav.appointments")}</p>
              <p className="mt-1 text-xs font-semibold text-platforma-muted">
                {formatDateTime(appointment.start_at)}
                {appointment.resource_name ? ` / ${appointment.resource_name}` : ""}
              </p>
            </div>
            <StatusBadge status={appointment.status} />
          </div>
          <div className="mt-3 grid gap-2 text-sm text-platforma-subtle sm:grid-cols-2">
            <p className="min-w-0 truncate font-semibold">{appointment.client_name || data.client?.full_name || t("deals.clientMissing")}</p>
            <p className="min-w-0 truncate font-semibold">{appointment.lead ? appointment.lead_title || t("crmCard.leadNumber", { id: appointment.lead }) : t("deals.notLinked")}</p>
          </div>
          {appointment.notes ? <p className="mt-3 text-sm leading-6 text-platforma-subtle">{appointment.notes}</p> : null}
        </div>
      ))}
      {!data.appointments.length ? <EmptyBlock title={t("nav.appointments")} text={t("appointments.emptyText")} /> : null}
    </div>
  );
}
