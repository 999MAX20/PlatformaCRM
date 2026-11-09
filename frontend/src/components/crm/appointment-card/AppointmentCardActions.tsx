import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, Check, CircleCheck, CircleX, UserX } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { appointmentsApi } from "../../../api/appointments";
import { resourcesApi } from "../../../api/resources";
import { useAuth } from "../../../features/auth/AuthProvider";
import { refreshAppointmentQueries } from "../../../lib/appointmentCache";
import { useI18n } from "../../../lib/i18n";
import type { CrmCardPayload } from "../../../types";
import { useActionConfirm } from "../../actions/ActionConfirmProvider";
import { AppointmentRescheduleForm } from "../../forms/AppointmentRescheduleForm";
import { useNotification } from "../../notifications/NotificationProvider";
import { ActionMenu, type ActionMenuItem } from "../../ui/ActionMenu";
import { Button } from "../../ui/Button";
import { Modal } from "../../ui/Modal";
import { ErrorState, LoadingState } from "../../ui/StateViews";
import { Textarea } from "../../ui/Textarea";

type StatusAction = "confirm" | "complete" | "cancel" | "no_show";
const labels = { confirm: "appointment.actionConfirm", complete: "appointment.actionComplete", cancel: "appointment.actionCancel", no_show: "appointment.actionNoShow" };

export function AppointmentCardActions({ data, timeZone, disabled, onPendingChange }: {
  data: CrmCardPayload; timeZone: string; disabled: boolean; onPendingChange: (value: boolean) => void;
}) {
  const appointment = data.appointment!;
  const { user } = useAuth();
  const { t } = useI18n();
  const cache = useQueryClient();
  const notify = useNotification();
  const confirm = useActionConfirm();
  const [reasonAction, setReasonAction] = useState<StatusAction | null>(null);
  const [reason, setReason] = useState("");
  const [version, setVersion] = useState(appointment.updated_at);
  const [reschedule, setReschedule] = useState(false);
  const [rescheduleDirty, setRescheduleDirty] = useState(false);
  const [reschedulePending, setReschedulePending] = useState(false);
  const busy = useRef(false);
  const closing = useRef(false);
  const resources = useQuery({ queryKey: ["resources", "appointment-card", appointment.business, user?.id], queryFn: resourcesApi.options, enabled: reschedule });
  const allowed = (id: string) => !appointment.is_archived && data.available_action_details?.some(action => action.id === id && action.allowed) === true;
  const mutation = useMutation({
    mutationFn: ({ action, reason, version }: { action: StatusAction; reason?: string; version: string }) => {
      if (action === "confirm") return appointmentsApi.confirm(appointment.id, version);
      if (action === "complete") return appointmentsApi.complete(appointment.id, version, reason);
      if (action === "cancel") return appointmentsApi.cancel(appointment.id, { reason: reason || "", expected_updated_at: version });
      return appointmentsApi.noShow(appointment.id, { reason: reason || "", expected_updated_at: version });
    },
    onSuccess: async updated => {
      await refreshAppointmentQueries(cache, updated);
      setReasonAction(null); setReason("");
      notify({ message: t("common.saved"), tone: "success" });
    },
  });
  // The parent cannot close or change entity underneath a nested action form.
  useEffect(() => { onPendingChange(mutation.isPending || reschedulePending || reschedule || !!reasonAction); return () => onPendingChange(false); }, [mutation.isPending, reschedulePending, reschedule, reasonAction, onPendingChange]);
  async function closeNested(kind: "reason" | "reschedule") {
    if (busy.current || mutation.isPending || closing.current) return;
    if (kind === "reason" ? !!reason.trim() : rescheduleDirty) {
      closing.current = true;
      const result = await confirm({ title: t("taskWorkspace.discardTitle"), confirmLabel: t("taskWorkspace.discard"), cancelLabel: t("taskWorkspace.keepEditing"), tone: "warning" });
      closing.current = false;
      if (!result.confirmed) return;
    }
    if (kind === "reason") { setReasonAction(null); setReason(""); mutation.reset(); }
    else { setReschedule(false); setRescheduleDirty(false); }
  }
  function act(action: StatusAction) {
    if (disabled || mutation.isPending || !allowed(action)) return;
    mutation.reset();
    if (action === "cancel" || action === "no_show" || (action === "complete" && Date.now() < Date.parse(appointment.end_at))) {
      setVersion(appointment.updated_at); setReason(""); setReasonAction(action);
    } else mutation.mutate({ action, version: appointment.updated_at });
  }
  const primary = allowed("confirm") ? "confirm" : allowed("complete") ? "complete" : null;
  const menu: ActionMenuItem[] = [];
  if (allowed("reschedule")) menu.push({ key: "reschedule", label: t("appointments.reschedule"), icon: CalendarClock, onSelect: () => setReschedule(true) });
  if (primary !== "complete" && allowed("complete")) menu.push({ key: "complete", label: t(labels.complete), icon: CircleCheck, onSelect: () => act("complete") });
  if (allowed("no_show")) menu.push({ key: "no_show", label: t(labels.no_show), icon: UserX, tone: "warning", onSelect: () => act("no_show") });
  if (allowed("cancel")) menu.push({ key: "cancel", label: t(labels.cancel), icon: CircleX, tone: "warning", onSelect: () => act("cancel") });
  const error = mutation.error ? <ErrorState error={mutation.error} action={<Button variant="secondary" onClick={async () => {
    try { const current = await appointmentsApi.get(appointment.id); await refreshAppointmentQueries(cache, current); setVersion(current.updated_at); mutation.reset(); }
    catch { /* Retain the original error and draft until refresh succeeds. */ }
  }}>{t("common.refresh")}</Button>} /> : null;
  return <div className="space-y-3">
    <div className="flex flex-wrap gap-2">
      {primary && <Button disabled={disabled} isLoading={mutation.isPending} onClick={() => act(primary)}><Check size={17} />{t(labels[primary])}</Button>}
      {!!menu.length && <ActionMenu label={t("clients.card.actions")} items={menu} disabled={disabled || mutation.isPending} overlay="modal" />}
    </div>
    {!reasonAction && error}
    <Modal open={!!reasonAction} title={reasonAction ? t(labels[reasonAction]) : ""} onClose={() => void closeNested("reason")}>
      <div className="space-y-4" data-testid="appointment-status-reason">
        <Textarea label={t(reasonAction === "complete" ? "records.earlyCompletion" : "appointments.statusReason")} value={reason} disabled={mutation.isPending} onChange={event => setReason(event.target.value)} />
        {error}
        <div className="flex justify-end gap-2"><Button variant="secondary" disabled={mutation.isPending} onClick={() => void closeNested("reason")}>{t("common.cancel")}</Button>
          <Button variant="warning" disabled={!reason.trim() || !reasonAction || !allowed(reasonAction)} isLoading={mutation.isPending} onClick={() => reasonAction && mutation.mutate({ action: reasonAction, reason: reason.trim(), version })}>{reasonAction && t(labels[reasonAction])}</Button></div>
      </div>
    </Modal>
    <Modal open={reschedule} title={t("appointments.rescheduleTitle")} onClose={() => void closeNested("reschedule")}>
      {resources.isPending ? <LoadingState /> : resources.error ? <ErrorState error={resources.error} action={<Button onClick={() => void resources.refetch()}>{t("common.retry")}</Button>} /> : <AppointmentRescheduleForm appointment={appointment} businessId={appointment.business} resources={resources.data || []} timeZone={timeZone} isSubmitting={reschedulePending} onDirtyChange={setRescheduleDirty} onCancel={() => void closeNested("reschedule")} onSubmit={async payload => {
        if (busy.current) return;
        busy.current = true; setReschedulePending(true);
        try { const updated = await appointmentsApi.reschedule({ id: appointment.id, payload }); await refreshAppointmentQueries(cache, updated); setReschedule(false); setRescheduleDirty(false); notify({ message: t("appointments.rescheduledNotice"), tone: "success" }); }
        finally { busy.current = false; setReschedulePending(false); }
      }} />}
    </Modal>
  </div>;
}
