import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, ClipboardList, MapPin, UserRound } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Link } from "react-router";
import { useActiveBusiness } from "../../../hooks/useBusiness";
import { AppointmentPlanPanel } from "../../../features/calendar/AppointmentPlanPanel";
import { AppointmentRescheduleForm } from "../../forms/AppointmentRescheduleForm";
import { Modal } from "../../ui/Modal";
import { EntityTimeline } from "./EntityTimeline";
import { EntityTasksPanel } from "./EntityTasksPanel";
import { useEntityData } from "../../../hooks/useEntityData";
import { appointmentsApi } from "../../../api/appointments";
import { formatDateTime } from "../../../lib/format";
import { refreshAppointmentQueries } from "../../../lib/appointmentCache";
import { useI18n } from "../../../lib/i18n";
import { usePatientRoute } from "../../../features/medical/PatientWorkspaceScope";
import type { CrmCardPayload } from "../../../types";
import { useNotification } from "../../notifications/NotificationProvider";
import { Button } from "../../ui/Button";
import { ErrorState, LoadingState } from "../../ui/StateViews";
import { StatusBadge } from "../../ui/StatusBadge";
import { Textarea } from "../../ui/Textarea";
import { EntityAttachmentsPanel } from "./EntityAttachmentsPanel";
import { EntityCustomFieldsPanel } from "./EntityCustomFieldsPanel";
import { drawerSurfaceClass, EmptyBlock, SummaryItem, getChannelLabel } from "./shared";
import type { CrmDrawerEntity } from "./types";

type AppointmentAction = "confirmed" | "cancelled" | "completed" | "no_show";

function sourceLabel(source: string, t: (key: string) => string) {
  return t(`appointment.source.${source}`) || getChannelLabel(source, t);
}

export function AppointmentDrawerContent({ data, entity }: { data: CrmCardPayload; entity: CrmDrawerEntity }) {
  const { t, language } = useI18n();
  const patientPath = usePatientRoute();
  const { business } = useActiveBusiness();
  const timeZone = business?.timezone || "Asia/Qyzylorda";
  const showNotification = useNotification();
  const queryClient = useQueryClient();
  const appointment = data.appointment;
  const { resources } = useEntityData({ resources: true });
  const canUpdate = !!appointment && !appointment.is_archived && data.available_action_details?.some(action => action.resource === "appointments" && action.action === "update" && action.allowed) === true;
  const [rescheduleOpen, setRescheduleOpen] = useState(false);
  const [reschedulePending, setReschedulePending] = useState(false);
  const rescheduleInFlight = useRef(false);
  const client = data.client;
  const [notes, setNotes] = useState(appointment?.notes || "");
  const [statusReasonAction, setStatusReasonAction] = useState<AppointmentAction | null>(null);
  const [statusReason, setStatusReason] = useState("");
  const [statusReasonVersion, setStatusReasonVersion] = useState("");

  useEffect(() => {
    setNotes(appointment?.notes || "");
  }, [appointment?.id, appointment?.notes]);

  const notesMutation = useMutation({
    mutationFn: async () => {
      if (!appointment) throw new Error("Appointment is required.");
      return appointmentsApi.update({ id: appointment.id, payload: { notes } });
    },
    onSuccess: (updated) => {
      void refreshAppointmentQueries(queryClient, updated);
      showNotification({ message: t("common.saved"), tone: "success" });
    },
  });

  const lifecycleMutation = useMutation({
    mutationFn: async ({ action, reason, expected_updated_at }: { action: AppointmentAction; reason?: string; expected_updated_at: string }) => {
      if (!appointment) throw new Error("Appointment is required.");
      if (action === "confirmed") return appointmentsApi.confirm(appointment.id, expected_updated_at);
      if (action === "cancelled") return appointmentsApi.cancel(appointment.id, { reason: reason || "", expected_updated_at });
      if (action === "completed") return appointmentsApi.complete(appointment.id, expected_updated_at, reason);
      return appointmentsApi.noShow(appointment.id, { reason: reason || "", expected_updated_at });
    },
    onSuccess: async (updated, variables) => {
      await refreshAppointmentQueries(queryClient, updated);
      setStatusReasonAction(null);
      setStatusReason("");
      const labels: Record<AppointmentAction, string> = {
        confirmed: t("appointment.statusConfirmed"),
        cancelled: t("appointment.statusCancelled"),
        completed: t("appointment.statusCompleted"),
        no_show: t("appointment.statusNoShow"),
      };
      showNotification({ message: labels[variables.action], tone: "success" });
    },
  });

  if (!appointment) return <EmptyBlock title={t("crmCard.appointmentNumber", { id: entity.id })} text={t("crmCard.loadError")} />;

  const isTerminal = ["cancelled", "completed", "no_show"].includes(appointment.status);
  const clientName = client?.full_name || appointment.client_name || `#${appointment.client}`;
  const serviceName = appointment.service_name || `#${appointment.service}`;
  const serviceMeta = appointment.service_duration_minutes ? `${serviceName} · ${appointment.service_duration_minutes} ${t("appointment.minutes")}` : serviceName;
  const resourceName = appointment.resource_name || (appointment.resource ? `#${appointment.resource}` : t("appointment.noResource"));

  return (
    <div className="space-y-4">
      <div className={drawerSurfaceClass}>
        <div className="flex flex-col gap-3">
          <div className="min-w-0">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <StatusBadge status={appointment.status} />
              <span className="rounded-full bg-surface-muted px-3 py-1 text-xs font-semibold text-platforma-muted">{sourceLabel(appointment.source, t)}</span>
            </div>
            <h3 className="break-words text-xl font-semibold text-platforma-ink">{clientName}</h3>
            {appointment.branch_name && <p className="mt-1 text-sm text-platforma-subtle">{appointment.branch_name} · {appointment.branch_address}</p>}
            <p className="mt-1 text-sm font-semibold text-platforma-muted">
              {formatDateTime(appointment.start_at, timeZone, true, language)}
            </p>
          </div>
          {canUpdate && <div className="flex shrink-0 flex-wrap gap-2">
            {!isTerminal && <Button size="sm" variant="secondary" disabled={lifecycleMutation.isPending} onClick={() => setRescheduleOpen(true)}>{t("appointments.reschedule")}</Button>}
            {appointment.status !== "confirmed" && !isTerminal ? (
              <Button size="sm" variant="secondary" isLoading={lifecycleMutation.isPending} onClick={() => lifecycleMutation.mutate({ action: "confirmed", expected_updated_at: appointment.updated_at })}>
                {t("appointment.actionConfirm")}
              </Button>
            ) : null}
            {!isTerminal ? (
              <Button size="sm" variant="secondary" isLoading={lifecycleMutation.isPending} onClick={() => { if (Date.now() < new Date(appointment.end_at).getTime()) { setStatusReasonAction("completed"); setStatusReasonVersion(appointment.updated_at); setStatusReason(""); } else lifecycleMutation.mutate({ action: "completed", expected_updated_at: appointment.updated_at }); }}>
                {t("appointment.actionComplete")}
              </Button>
            ) : null}
            {appointment.status !== "no_show" && !isTerminal ? (
              <Button size="sm" variant="warning" isLoading={lifecycleMutation.isPending} onClick={() => { setStatusReasonAction("no_show"); setStatusReasonVersion(appointment.updated_at); setStatusReason(""); }}>
                {t("appointment.actionNoShow")}
              </Button>
            ) : null}
            {!isTerminal ? (
              <Button size="sm" variant="warning" isLoading={lifecycleMutation.isPending} onClick={() => { setStatusReasonAction("cancelled"); setStatusReasonVersion(appointment.updated_at); setStatusReason(""); }}>
                {t("appointment.actionCancel")}
              </Button>
            ) : null}
          </div>}
        </div>
        {statusReasonAction ? (
          <div className="mt-4 rounded-lg border border-platforma-border bg-surface-muted p-3">
            <Textarea
              value={statusReason}
              onChange={(event) => setStatusReason(event.target.value)}
              label={t(statusReasonAction === "completed" ? "records.earlyCompletion" : "appointments.statusReason")}
              placeholder={t(statusReasonAction === "completed" ? "records.earlyCompletionReason" : "appointments.statusReasonPlaceholder")}
            />
            <div className="mt-3 flex justify-end gap-2">
              <Button type="button" size="sm" variant="secondary" onClick={() => { setStatusReasonAction(null); setStatusReason(""); }}>
                {t("common.cancel")}
              </Button>
              <Button
                type="button"
                size="sm"
                variant="warning"
                isLoading={lifecycleMutation.isPending}
                disabled={!statusReason.trim()}
                onClick={() => lifecycleMutation.mutate({ action: statusReasonAction, reason: statusReason.trim(), expected_updated_at: statusReasonVersion })}
              >
                {statusReasonAction === "completed" ? t("appointment.actionComplete") : statusReasonAction === "cancelled" ? t("appointment.actionCancel") : t("appointment.actionNoShow")}
              </Button>
            </div>
          </div>
        ) : null}
        {notesMutation.error || lifecycleMutation.error ? <div className="mt-3"><ErrorState error={notesMutation.error || lifecycleMutation.error} action={<Button type="button" onClick={() => {
          setStatusReasonAction(null);
          void refreshAppointmentQueries(queryClient);
        }}>{t("common.refresh")}</Button>} /></div> : null}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <SummaryItem icon={ClipboardList} label={t("appointment.service")} value={serviceMeta} />
        <SummaryItem icon={CalendarClock} label={t("appointment.resource")} value={resourceName} />
        {appointment.responsible_user_name && <SummaryItem icon={UserRound} label={t("appointment.responsible")} value={appointment.responsible_user_name} />}
        {appointment.branch_name && <SummaryItem icon={MapPin} label={t("records.branch")} value={appointment.branch_name} />}
      </div>

      {client && <Link className="platforma-focus-ring inline-flex rounded py-2 text-brand-700" to={patientPath(`/app/clients/${client.id}`)}>{t("leads.openClient")}</Link>}

      <div className={drawerSurfaceClass}>
        <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="font-semibold text-platforma-ink">{t("appointment.notes")}</h3>
          </div>
          <Button type="button" variant="secondary" disabled={!canUpdate} isLoading={notesMutation.isPending} onClick={() => notesMutation.mutate()}>
            {t("clients.save")}
          </Button>
        </div>
        <Textarea aria-label={t("appointment.notes")} readOnly={!canUpdate} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder={t("crmCard.commentPlaceholder")} />
      </div>
      <AppointmentPlanPanel appointment={appointment} timeZone={timeZone} />
      <section className="space-y-3"><h3 className="font-semibold">{t("tasks.history")}</h3><EntityTimeline data={data} /></section>
      <section className="space-y-3"><h3 className="font-semibold">{t("nav.tasks")}</h3><EntityTasksPanel data={data} entity={entity} /></section>
      <EntityCustomFieldsPanel data={data} entity={entity} />
      <EntityAttachmentsPanel data={data} entity={entity} readOnly={!canUpdate} />
      <Modal open={rescheduleOpen} title={t("appointments.rescheduleTitle")} onClose={() => { if (!rescheduleInFlight.current) setRescheduleOpen(false); }}>
        {resources.isPending ? <LoadingState /> : resources.error ? <ErrorState error={resources.error} action={<Button onClick={() => void resources.refetch()}>{t("common.retry")}</Button>} /> : <AppointmentRescheduleForm appointment={appointment} businessId={appointment.business} resources={resources.data || []} isSubmitting={reschedulePending} onCancel={() => { if (!rescheduleInFlight.current) setRescheduleOpen(false); }} onSubmit={async payload => {
          if (rescheduleInFlight.current) return;
          rescheduleInFlight.current = true;
          setReschedulePending(true);
          try {
            const updated = await appointmentsApi.reschedule({ id: appointment.id, payload });
            await refreshAppointmentQueries(queryClient, updated);
            setRescheduleOpen(false);
            showNotification({ message: t("appointments.rescheduledNotice"), tone: "success" });
          } finally { rescheduleInFlight.current = false; setReschedulePending(false); }
        }} />}
      </Modal>
    </div>
  );
}
