import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { appointmentsApi } from "../../../api/appointments";
import { AppointmentPlanPanel } from "../../../features/calendar/AppointmentPlanPanel";
import { refreshAppointmentQueries } from "../../../lib/appointmentCache";
import { formatDateTime } from "../../../lib/format";
import { useI18n } from "../../../lib/i18n";
import type { CrmCardPayload } from "../../../types";
import { useNotification } from "../../notifications/NotificationProvider";
import { Button } from "../../ui/Button";
import { ErrorState } from "../../ui/StateViews";
import { Textarea } from "../../ui/Textarea";
import { formatTimelineEventText } from "../drawers/timelineHelpers";

export function AppointmentCardOverview({ data, timeZone, canEdit, onDirtyChange, onPendingChange, onHistory }: {
  data: CrmCardPayload; timeZone: string; canEdit: boolean;
  onDirtyChange: (value: boolean) => void; onPendingChange: (value: boolean) => void; onHistory: () => void;
}) {
  const appointment = data.appointment!;
  const { t, language } = useI18n();
  const cache = useQueryClient();
  const notify = useNotification();
  const [draft, setDraft] = useState<string | null>(null);
  const notes = draft ?? appointment.notes ?? "";
  const dirty = draft !== null && draft !== (appointment.notes || "");
  const mutation = useMutation({
    mutationFn: (notes: string) => appointmentsApi.update({ id: appointment.id, payload: { notes } }),
    onSuccess: async updated => {
      await refreshAppointmentQueries(cache, updated); setDraft(null);
      notify({ message: t("common.saved"), tone: "success" });
    },
  });
  useEffect(() => { onDirtyChange(dirty); return () => onDirtyChange(false); }, [dirty, onDirtyChange]);
  useEffect(() => { onPendingChange(mutation.isPending); return () => onPendingChange(false); }, [mutation.isPending, onPendingChange]);
  return <div className="space-y-6">
    <section className="space-y-3">
      <Textarea label={t("appointment.notes")} value={notes} readOnly={!canEdit} disabled={mutation.isPending} onChange={event => setDraft(event.target.value)} />
      {canEdit && <div className="flex justify-end"><Button variant="secondary" disabled={!dirty} isLoading={mutation.isPending} onClick={() => mutation.mutate(notes)}>{t("clients.save")}</Button></div>}
      {mutation.error && <ErrorState error={mutation.error} action={<Button variant="secondary" onClick={() => mutation.mutate(notes)}>{t("common.retry")}</Button>} />}
    </section>
    <AppointmentPlanPanel appointment={appointment} timeZone={timeZone} />
    <section><div className="mb-3 flex items-center justify-between gap-3"><h3 className="font-semibold">{t("clients.card.activity")}</h3><Button variant="ghost" onClick={onHistory}>{t("crmCard.timeline")}</Button></div>
      {data.timeline.length ? <ol className="space-y-4 border-l border-platforma-border pl-4">{data.timeline.slice(0, 3).map(event => <li key={event.id} className="relative before:absolute before:-left-[21px] before:top-2 before:h-2 before:w-2 before:rounded-full before:bg-platforma-subtle">
        <p className="whitespace-pre-wrap break-words text-sm font-medium">{event.event_type === "visit_plan_changed" ? formatTimelineEventText(event, t) : event.text || event.event_type}</p>
        <time className="text-xs text-platforma-subtle">{formatDateTime(event.created_at, timeZone, true, language)}</time>
      </li>)}</ol> : <p className="text-sm text-platforma-subtle">{t("crmCard.emptyTimelineText")}</p>}
    </section>
  </div>;
}
