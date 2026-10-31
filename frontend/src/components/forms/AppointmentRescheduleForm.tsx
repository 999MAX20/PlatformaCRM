import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { appointmentsApi, type AppointmentReschedulePayload } from "../../api/appointments";
import { dateInTimeZone, todayInTimeZone } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import { useBranchBooking } from "../../hooks/useBranchBooking";
import type { Appointment, Id, Resource } from "../../types";
import { useActionFeedback } from "../actions/useActionFeedback";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";
import { ErrorState, LoadingState } from "../ui/StateViews";
import { Textarea } from "../ui/Textarea";

export function AppointmentRescheduleForm({
  appointment,
  businessId,
  resources,
  onSubmit,
  onCancel,
  isSubmitting,
  timeZone = "UTC",
}: {
  appointment: Appointment;
  businessId: Id;
  resources: Resource[];
  onSubmit: (payload: AppointmentReschedulePayload) => Promise<unknown>;
  onCancel: () => void;
  isSubmitting?: boolean;
  timeZone?: string;
}) {
  const { t, language } = useI18n();
  const { getRecoverableMessage } = useActionFeedback();
  const branch = useBranchBooking(businessId, appointment.branch);
  const locale = language === "en" ? "en-US" : language === "kk" ? "kk-KZ" : "ru-RU";
  const [date, setDate] = useState(dateInTimeZone(appointment.start_at, timeZone) || todayInTimeZone(timeZone));
  const [expectedVersion] = useState(appointment.updated_at);
  const [resource, setResource] = useState(appointment.resource ? String(appointment.resource) : "");
  const [slot, setSlot] = useState("");
  const [reason, setReason] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const activeResources = resources.filter((item) => item.is_active && !item.retired_at && item.resource_type === "staff" && (!branch.enabled || branch.catalog?.assignments.some((assignment) => assignment.resource === item.id && assignment.service_ids.includes(appointment.service))));
  useEffect(() => { setSlot(""); }, [branch.branchId]);
  useEffect(() => {
    if (branch.ready && branch.enabled && !branch.catalog?.assignments.some((item) => item.resource === Number(resource) && item.service_ids.includes(appointment.service))) setResource("");
  }, [branch.ready, branch.enabled, branch.catalog, resource, appointment.service]);

  const slots = useQuery({
    queryKey: ["available-slots", businessId, appointment.service, resource, date, "reschedule", appointment.id, branch.branchId],
    queryFn: () =>
      appointmentsApi.availableSlots({
        business_id: businessId,
        branch_id: branch.branchId ? Number(branch.branchId) : "",
        service_id: appointment.service,
        resource_id: resource ? Number(resource) : "",
        date,
        exclude_appointment_id: appointment.id,
      }),
    enabled: Boolean(branch.ready && businessId && appointment.service && resource && date),
  });

  const slotOptions = useMemo(
    () =>
      (slots.data || []).map((item) => ({
        value: item.start_at,
        label: `${new Date(item.start_at).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit", timeZone })} - ${new Date(item.end_at).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit", timeZone })}`,
      })),
    [locale, slots.data, timeZone],
  );

  return (
    <form
      data-testid="appointment-reschedule-form"
      className="space-y-4"
      onSubmit={async (event) => {
        event.preventDefault();
        if (!branch.ready || !resource || !slot) {
          setSubmitError(t("appointment.selectSlotError"));
          return;
        }
        setSubmitError(null);
        try {
          await onSubmit({
            start_at: slot,
            expected_updated_at: expectedVersion,
            ...(branch.branchId ? { branch: Number(branch.branchId) } : {}),
            resource: resource ? Number(resource) : null,
            reason: reason.trim(),
          });
        } catch (error) {
          setSubmitError(getRecoverableMessage(error));
        }
      }}
    >
      {branch.error && <ErrorState error={branch.error} />}
      {branch.enabled && <Select label={t("branches.branch")} value={branch.branchId} onChange={(event) => branch.setBranchId(event.target.value)} options={[{ value: "", label: t("branches.choose") }, ...branch.branches.map((item) => ({ value: item.id, label: `${item.name} · ${item.address}` }))]} />}
      <div className="rounded-card border border-platforma-border bg-surface-muted p-3 text-sm font-semibold text-platforma-subtle">
        {t("appointments.currentTime")}: {new Date(appointment.start_at).toLocaleString(locale, { dateStyle: "medium", timeStyle: "short", timeZone })}
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Input
          data-testid="appointment-reschedule-date"
          label={t("appointment.date")}
          type="date"
          value={date}
          onChange={(event) => {
            setDate(event.target.value);
            setSlot("");
          }}
        />
        <Select
          data-testid="appointment-reschedule-resource"
          label={t("appointment.resource")}
          value={resource}
          onChange={(event) => {
            setResource(event.target.value);
            setSlot("");
          }}
          options={[{ value: "", label: t("appointment.selectSpecialist") }, ...activeResources.map((item) => ({ value: String(item.id), label: item.name }))]}
        />
      </div>
      {slots.isLoading ? <LoadingState /> : null}
      {!slots.isLoading ? (
        <Select
          data-testid="appointment-reschedule-slot"
          label={t("appointment.time")}
          value={slot}
          onChange={(event) => setSlot(event.target.value)}
          options={[{ value: "", label: slotOptions.length ? t("appointments.selectNewSlot") : t("appointments.noSlots") }, ...slotOptions]}
        />
      ) : null}
      <Textarea label={t("appointments.rescheduleReason")} value={reason} onChange={(event) => setReason(event.target.value)} placeholder={t("appointments.rescheduleReasonPlaceholder")} />
      {submitError || slots.error ? (
        <ErrorState
          message={submitError || getRecoverableMessage(slots.error)}
        />
      ) : null}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          {t("common.cancel")}
        </Button>
        <Button data-testid="appointment-reschedule-submit" type="submit" isLoading={isSubmitting} disabled={!branch.ready || !slot || !resource}>
          {t("appointments.reschedule")}
        </Button>
      </div>
    </form>
  );
}
