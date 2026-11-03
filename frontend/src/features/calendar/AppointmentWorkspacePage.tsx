import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, Check, RotateCcw, X } from "lucide-react";
import type { ReactNode } from "react";
import { useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router";
import { EntityCustomFieldsPanel } from "../../components/crm/drawers/EntityCustomFieldsPanel";
import { EntityAttachmentsPanel } from "../../components/crm/drawers/EntityAttachmentsPanel";

import {
  appointmentsApi,
  type AppointmentReschedulePayload,
} from "../../api/appointments";
import { crmCardsApi } from "../../api/crmCards";
import { normalizeAppError } from "../../api/appError";
import { useActionConfirm } from "../../components/actions/ActionConfirmProvider";
import { useActionFeedback } from "../../components/actions/useActionFeedback";
import {
  EntityWorkspaceEmptyState,
  EntityWorkspaceAside,
  EntityWorkspaceAvatar,
  EntityWorkspaceBody,
  EntityWorkspaceHeader,
  EntityWorkspaceLoadingState,
  EntityWorkspaceMain,
  EntityWorkspaceMetrics,
  EntityWorkspaceRoot,
} from "../../components/crm";
import { AppointmentRescheduleForm } from "../../components/forms/AppointmentRescheduleForm";
import { formatTimelineEventText } from "../../components/crm/drawers/timelineHelpers";
import { Button } from "../../components/ui/Button";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { Badge } from "../../components/ui/Badge";
import { ErrorState } from "../../components/ui/StateViews";
import { Modal } from "../../components/ui/Modal";
import { formatDateTime } from "../../lib/format";
import { refreshAppointmentQueries } from "../../lib/appointmentCache";
import { useI18n } from "../../lib/i18n";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useEntityData } from "../../hooks/useEntityData";
import type { ActivityEvent, Appointment, Task } from "../../types";
import { useAuth } from "../auth/AuthProvider";
import { recordReturnPath } from "./recordFilters";
import { hasPermission } from "../../lib/permissions";
import { TaskEditor } from "../tasks/components/TaskEditor";

function asNumericId(value: string | undefined): number | null {
  const id = Number(value);
  return Number.isFinite(id) && id > 0 ? id : null;
}

function getAllowedStatusActions(appointment: Appointment) {
  if (appointment.status === "created" || appointment.status === "rescheduled")
    return ["confirmed", "completed", "cancelled", "no_show"] as Appointment["status"][];
  if (appointment.status === "confirmed")
    return ["completed", "cancelled", "no_show"] as Appointment["status"][];
  return [] as Appointment["status"][];
}

export function AppointmentWorkspacePage() {
  const { t, language } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
  const confirmAction = useActionConfirm();
  const { notifyError, notifySuccess } = useActionFeedback();
  const queryClient = useQueryClient();
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const { resources } = useEntityData({ resources: true });
  const { id: routeId } = useParams();
  const appointmentId = asNumericId(routeId);
  const reschedulePending = useRef(false);
  const [rescheduleOpen, setRescheduleOpen] = useState(false);
  const [taskOpen, setTaskOpen] = useState(false);

  const cardQuery = useQuery({
    queryKey: ["crm-card", "appointment", appointmentId, business?.id, user?.id],
    queryFn: () =>
      crmCardsApi.get({ type: "appointment", id: appointmentId as number, business: business?.id }),
    enabled: Boolean(appointmentId && business),
  });

  const appointment = cardQuery.data?.appointment || null;
  const client = cardQuery.data?.client || null;
  const lead = cardQuery.data?.lead || null;
  const tasks = cardQuery.data?.tasks || [];
  const timeline = cardQuery.data?.timeline || [];
  const canUpdateAppointment = !!appointment && !appointment.is_archived &&
    cardQuery.data?.available_action_details?.some(action =>
      action.resource === "appointments" && action.action === "update" && action.allowed) === true;
  const statusActions =
    appointment && canUpdateAppointment
      ? getAllowedStatusActions(appointment)
      : [];
  const canReschedule =
    appointment && canUpdateAppointment
      ? !["completed", "cancelled", "no_show"].includes(appointment.status)
      : false;

  const invalidateAppointment = async (updated?: Appointment) => {
    await refreshAppointmentQueries(queryClient, updated);
  };

  const statusMutation = useMutation<
    Appointment,
    Error,
    { status: Appointment["status"]; reason?: string; expected_updated_at: string }
  >({
    mutationFn: ({ status, reason, expected_updated_at }) => {
      if (!appointmentId) throw new Error(t("appointments.title"));
      if (status === "confirmed") return appointmentsApi.confirm(appointmentId, expected_updated_at);
      if (status === "cancelled")
        return appointmentsApi.cancel(appointmentId, { reason: reason || "", expected_updated_at });
      if (status === "completed")
        return appointmentsApi.complete(appointmentId, expected_updated_at, reason);
      if (status === "no_show")
        return appointmentsApi.noShow(appointmentId, { reason: reason || "", expected_updated_at });
      return appointmentsApi.get(appointmentId);
    },
    onSuccess: async (updated) => {
      notifySuccess(t("appointments.actionDone"));
      await invalidateAppointment(updated);
    },
    onError: (error) => notifyError(error, { actionLabel: t("common.refresh"), retry: () => invalidateAppointment() }),
  });

  const rescheduleMutation = useMutation<
    Appointment,
    Error,
    AppointmentReschedulePayload
  >({
    mutationFn: (payload) => {
      if (!appointmentId) throw new Error(t("appointments.title"));
      reschedulePending.current = true;
      return appointmentsApi.reschedule({ id: appointmentId, payload });
    },
    onSettled: () => { reschedulePending.current = false; },
    onSuccess: async (updated) => {
      setRescheduleOpen(false);
      notifySuccess(t("appointments.rescheduledNotice"));
      await invalidateAppointment(updated);
    },
    onError: (error) =>
      notifyError(error, {
        actionLabel: t("common.refresh"),
        retry: () => invalidateAppointment(),
      }),
  });

  async function requestReasonAction(status: Appointment["status"]) {
    const expected_updated_at = appointment?.updated_at;
    if (!expected_updated_at) return;
    const result = await confirmAction({
      title: t(status === "completed" ? "records.earlyCompletion" : "appointments.statusReasonTitle"),
      description: t(status === "completed" ? "records.earlyCompletionReason" : "appointments.statusReasonPlaceholder"),
      confirmLabel: getAppointmentActionLabel(status, t),
      tone: "warning",
      reason: {
        label: t("appointments.statusReason"),
        placeholder: t(status === "completed" ? "records.earlyCompletionReason" : "appointments.statusReasonPlaceholder"),
        required: true,
        minLength: 3,
      },
    });
    if (!result.confirmed || !result.reason) return;
    statusMutation.mutate({ status, reason: result.reason, expected_updated_at });
  }

  if (!appointmentId)
    return <EntityWorkspaceEmptyState title={t("records.legacyUnavailable")} />;
  if (cardQuery.isLoading || resources.isLoading)
    return <EntityWorkspaceLoadingState />;
  const pageError = cardQuery.error || resources.error;
  if (pageError && normalizeAppError(pageError).status === 404)
    return <EntityWorkspaceEmptyState title={t("actions.errorUnavailable")} />;
  if (pageError)
    return (
      <EntityWorkspaceRoot><ErrorState error={pageError} action={<Button variant="secondary" onClick={() => { void cardQuery.refetch(); void resources.refetch(); }}>{t("common.retry")}</Button>} /></EntityWorkspaceRoot>
    );
  if (!appointment) {
    return (
      <EntityWorkspaceEmptyState
        title={t("appointments.title")}
        description={t("calendar.freeDayHint")}
      />
    );
  }

  const title =
    client?.full_name || appointment.client_name || t("common.client");
  const isPlanned = ["created", "confirmed", "rescheduled"].includes(appointment.status);
  const subtitle = [
    appointment.service_name || t("common.service"),
    formatDateTime(appointment.start_at, business?.timezone, true, language),
    appointment.resource_name || t("appointment.noResource"),
  ]
    .filter(Boolean)
    .join(" / ");

  return (
    <>
      <EntityWorkspaceRoot>
        <EntityWorkspaceHeader
          backLabel={t("common.back")}
          onBack={() => navigate(recordReturnPath(location.state?.recordReturnTo))}
          avatar={
            <EntityWorkspaceAvatar>
              {title.slice(0, 2).toUpperCase()}
            </EntityWorkspaceAvatar>
          }
          title={title}
          subtitle={subtitle}
          status={isPlanned ? undefined : appointment.status}
          actions={
            <>
              {client ? (
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => navigate(`/app/clients/${client.id}`)}
                >
                  {t("leads.openClient")}
                </Button>
              ) : null}
              {lead ? (
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => navigate(`/app/leads/${lead.id}`)}
                >
                  {t("crmCard.leadNumber", { id: lead.id })}
                </Button>
              ) : null}
            </>
          }
        />

        <EntityWorkspaceMetrics>
          <AppointmentMetric
            label={t("tasks.status")}
            value={isPlanned ? t("records.planned") : t(`status.${appointment.status}`)}
          />
          <AppointmentMetric
            label={t("records.service")}
            value={appointment.service_name || t("common.service")}
          />
          <AppointmentMetric
            label={t("appointment.resource")}
            value={appointment.resource_name || t("appointment.noResource")}
          />
          <AppointmentMetric
            label={t("tasks.dueAt")}
            value={formatDateTime(appointment.start_at, business?.timezone, true, language)}
          />
          <AppointmentMetric label={t("nav.tasks")} value={cardQuery.data?.meta?.related_counts.tasks ?? tasks.length} />
        </EntityWorkspaceMetrics>

        <EntityWorkspaceBody>
          <EntityWorkspaceAside>
            <AppointmentSection title={t("calendar.visit")}>
              <div className="flex flex-wrap gap-2">
                {isPlanned ? <Badge variant="info">{t("records.planned")}</Badge> : <StatusBadge status={appointment.status} />}
                {appointment.status === "confirmed" ? <StatusBadge status="confirmed" /> : null}
              </div>
              <div className="mt-3 space-y-2 text-sm font-semibold text-platforma-subtle">
                {appointment.responsible_user_name && <MetaRow label={t("appointment.responsible")} value={appointment.responsible_user_name} />}
                {appointment.branch_name && <MetaRow label={t("branches.branch")} value={`${appointment.branch_name} · ${appointment.branch_address}`} />}
                <MetaRow
                  label={t("tasks.dueAt")}
                  value={formatDateTime(appointment.start_at, business?.timezone, true, language)}
                />
                <MetaRow
                  label={t("appointment.source")}
                  value={t(`appointment.source.${appointment.source}`)}
                />
                {appointment.notes ? (
                  <p className="rounded-control bg-surface-subtle p-3 leading-6">
                    {appointment.notes}
                  </p>
                ) : null}
              </div>
            </AppointmentSection>

            <AppointmentSection title={t("appointments.actions")}>
              <div className="grid gap-2">
                {statusActions.map((status, index) => (
                  <Button
                    key={status}
                    data-appointment-action-id={status}
                    type="button"
                    variant={
                      status === "cancelled" || status === "no_show"
                        ? "warning"
                        : index === 0
                          ? "primary"
                          : "secondary"
                    }
                    isLoading={statusMutation.isPending}
                    onClick={() => {
                      if (status === "cancelled" || status === "no_show" || (status === "completed" && Date.now() < new Date(appointment.end_at).getTime()))
                        void requestReasonAction(status);
                      else statusMutation.mutate({ status, expected_updated_at: appointment.updated_at });
                    }}
                  >
                    {getAppointmentActionIcon(status)}
                    {getAppointmentActionLabel(status, t)}
                  </Button>
                ))}
                {canReschedule ? (
                  <Button
                    data-appointment-action-id="reschedule"
                    type="button"
                    variant="secondary"
                    onClick={() => setRescheduleOpen(true)}
                  >
                    <RotateCcw size={16} /> {t("appointments.reschedule")}
                  </Button>
                ) : null}
                {appointment.visit_plan ? <Button variant="secondary" onClick={() => navigate(`/app/appointments?view=plans&plan=${appointment.visit_plan}`)}>{t("plans.plan")}</Button> : null}
                {hasPermission(user, business?.id, "appointments", "create") && client ? <Button variant="secondary" onClick={() => navigate(`/app/appointments?create=1&client=${client.id}&service=${appointment.service || ""}&resource=${appointment.resource || ""}&branch=${appointment.branch || ""}`)}>{t("appointments.repeatBooking")}</Button> : null}
                {hasPermission(user, business?.id, "tasks", "create") ? <Button variant="secondary" onClick={() => setTaskOpen(true)}>{t("taskWorkspace.create")}</Button> : null}
                <Button variant="secondary" onClick={() => navigate(`/app/calendar?appointment=${appointment.id}`)}>{t("nav.calendar")}</Button>
              </div>
            </AppointmentSection>
          </EntityWorkspaceAside>

          <EntityWorkspaceMain>
            {cardQuery.data?.custom_fields.length ? <div className="lg:col-span-2"><EntityCustomFieldsPanel data={cardQuery.data} entity={{ type: "appointment", id: appointment.id }} /></div> : null}
            <AppointmentSection title={t("tasks.links")}>
              <div className="flex flex-wrap gap-2">
                {client ? (
                  <EntityLink
                    onClick={() => navigate(`/app/clients/${client.id}`)}
                  >
                    {client.full_name || t("common.client")}
                  </EntityLink>
                ) : null}
                {lead ? (
                  <EntityLink onClick={() => navigate(`/app/leads/${lead.id}`)}>
                    {t("crmCard.leadNumber", { id: lead.id })}
                  </EntityLink>
                ) : null}
                {appointment.source_conversation ? <EntityLink onClick={() => navigate(`/app/conversations/${appointment.source_conversation}`)}>{t("nav.conversations")}</EntityLink> : null}
                {!client && !lead ? (
                  <p className="text-sm font-semibold text-platforma-subtle">
                    {t("tasks.noLinkedEntities")}
                  </p>
                ) : null}
              </div>
            </AppointmentSection>

            <AppointmentSection title={t("nav.tasks")}>
              <div className="space-y-2">
                {tasks.map((task) => (
                  <TaskRow
                    key={task.id}
                    task={task}
                    onOpen={() => navigate(`/app/tasks/${task.id}`)}
                  />
                ))}
                {cardQuery.data?.meta?.has_more.tasks ? <Link className="platforma-focus-ring text-brand-700" to={`/app/tasks?tab=all&appointment_ids=${appointment.id}`}>{t("nav.tasks")}</Link> : null}
                {!tasks.length ? (
                  <p className="text-sm font-semibold text-platforma-subtle">
                    {t("taskWorkspace.empty")}
                  </p>
                ) : null}
              </div>
            </AppointmentSection>

            <AppointmentSection
              title={t("tasks.history")}
              className="lg:col-span-2"
            >
              <div className="space-y-2">
                {timeline.map((event) => (
                  <ActivityRow key={event.id} event={event} />
                ))}
                {cardQuery.data?.meta?.has_more.timeline ? <Link className="platforma-focus-ring text-brand-700" to={`/app/timeline?entity_type=Appointment&entity_id=${appointment.id}`}>{t("nav.timeline")}</Link> : null}
                {!timeline.length ? (
                  <p className="text-sm font-semibold text-platforma-subtle">
                    {t("tasks.noHistory")}
                  </p>
                ) : null}
              </div>
            </AppointmentSection>
            {cardQuery.data ? <EntityAttachmentsPanel data={cardQuery.data} entity={{ type: "appointment", id: appointment.id }} readOnly={!canUpdateAppointment} /> : null}
          </EntityWorkspaceMain>
        </EntityWorkspaceBody>
      </EntityWorkspaceRoot>

      <Modal
        title={t("appointments.rescheduleTitle")}
        open={rescheduleOpen}
        onClose={() => { if (!reschedulePending.current) setRescheduleOpen(false); }}
      >
        <AppointmentRescheduleForm
          appointment={appointment}
          businessId={appointment.business}
          resources={resources.data || []}
          onCancel={() => { if (!reschedulePending.current) setRescheduleOpen(false); }}
          onSubmit={(payload) => rescheduleMutation.mutateAsync(payload)}
          isSubmitting={rescheduleMutation.isPending}
          timeZone={business?.timezone || "Asia/Almaty"}
        />
      </Modal>
      {taskOpen ? <TaskEditor business={appointment.business} zone={business?.timezone || "UTC"} initialClient={client?.id} initialAppointment={appointment.id} onClose={() => setTaskOpen(false)} onSaved={async () => { setTaskOpen(false); await invalidateAppointment(); }} /> : null}
    </>
  );
}

function getAppointmentActionLabel(
  status: Appointment["status"],
  t: (key: string) => string,
) {
  if (status === "confirmed") return t("appointment.actionConfirm");
  if (status === "completed") return t("appointment.actionComplete");
  if (status === "cancelled") return t("appointment.actionCancel");
  if (status === "no_show") return t("appointment.actionNoShow");
  return t(`status.${status}`);
}

function getAppointmentActionIcon(status: Appointment["status"]) {
  if (status === "confirmed" || status === "completed")
    return <Check size={16} />;
  if (status === "cancelled" || status === "no_show") return <X size={16} />;
  return <CalendarClock size={16} />;
}

function AppointmentMetric({
  label,
  value,
}: {
  label: string;
  value: ReactNode;
}) {
  return (
    <div className="rounded-card border border-platforma-border bg-platforma-card px-4 py-3">
      <p className="text-xs font-semibold uppercase text-platforma-muted">{label}</p>
      <p className="mt-1 truncate text-sm font-bold text-platforma-text">{value}</p>
    </div>
  );
}

function AppointmentSection({
  title,
  className,
  children,
}: {
  title: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={className}>
      <h2 className="mb-3 text-sm font-semibold text-platforma-text">{title}</h2>
      <div className="rounded-card border border-platforma-border bg-platforma-card p-4 shadow-platforma-card">
        {children}
      </div>
    </section>
  );
}

function MetaRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-control bg-surface-subtle px-3 py-2">
      <span>{label}</span>
      <span className="text-right text-platforma-text">{value}</span>
    </div>
  );
}

function EntityLink({
  onClick,
  children,
}: {
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      className="rounded-full bg-brand-50 px-3 py-1.5 text-sm font-semibold text-brand-700 transition hover:bg-brand-100"
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function TaskRow({ task, onOpen }: { task: Task; onOpen: () => void }) {
  const { t, language } = useI18n();
  return (
    <button
      type="button"
      className="w-full rounded-card border border-platforma-border bg-surface-subtle p-3 text-left transition hover:border-brand-200 hover:bg-brand-50"
      onClick={onOpen}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-platforma-text">
            {task.title}
          </p>
          <p className="mt-1 text-xs font-semibold text-platforma-muted">
            {task.due_at ? formatDateTime(task.due_at, undefined, false, language) : t("tasks.groupNoDue")}
          </p>
        </div>
        <StatusBadge status={task.status} />
      </div>
    </button>
  );
}

function ActivityRow({ event }: { event: ActivityEvent }) {
  const { t, language } = useI18n();
  const labels: Record<string, string> = {
    appointment_confirmed: "status.confirmed", appointment_completed: "records.completed",
    appointment_cancelled: "records.cancelled", appointment_no_show: "records.no_show",
    appointment_rescheduled: "appointments.rescheduledNotice",
  };
  const previousTime = event.metadata?.previous_start_at;
  const currentTime = event.metadata?.start_at;
  return (
    <div className="flex gap-3 rounded-card bg-surface-subtle p-3">
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-control bg-platforma-card text-brand-600">
        <CalendarClock size={16} />
      </span>
      <div className="min-w-0">
        <p className="text-sm font-semibold text-platforma-text">
          {labels[event.event_type] ? t(labels[event.event_type]) : formatTimelineEventText(event, t)}
        </p>
        {typeof previousTime === "string" && typeof currentTime === "string" ? <p className="mt-1 text-sm text-platforma-subtle">{formatDateTime(previousTime, undefined, false, language)} → {formatDateTime(currentTime, undefined, false, language)}</p> : null}
        {typeof event.metadata?.reason === "string" && event.metadata.reason ? <p className="mt-1 whitespace-pre-wrap break-words text-sm text-platforma-subtle">{t("crmCard.timelineFieldReason")}: {event.metadata.reason}</p> : null}
        <p className="mt-1 text-xs font-semibold text-platforma-muted">
          {formatDateTime(event.created_at, undefined, false, language)}
        </p>
      </div>
    </div>
  );
}
