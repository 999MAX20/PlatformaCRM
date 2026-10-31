import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router";
import { z } from "zod";

import { appointmentsApi, type AppointmentCreatePayload } from "../../api/appointments";
import { teamApi } from "../../api/team";
import { useAuth } from "../../features/auth/AuthProvider";
import { hasPermission } from "../../lib/permissions";
import { ClientPicker } from "./ClientPicker";
import { scheduleExceptionsApi, workingHoursApi } from "../../api/workingHours";
import { dateInTimeZone, formatMoney, hourInTimeZone, todayInTimeZone } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import { useBranchBooking } from "../../hooks/useBranchBooking";
import type { Appointment, Client, Id, Lead, Resource, Service, WorkingHours } from "../../types";
import { useActionFeedback } from "../actions/useActionFeedback";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";
import { ErrorState } from "../ui/StateViews";
import { StatusNotice } from "../ui/StatusNotice";
import { Textarea } from "../ui/Textarea";

function createSchema(t: (key: string) => string) {
  return z.object({
    client: z.coerce.number<string | number>().min(1, t("appointment.selectClient")),
    service: z.coerce.number<string | number>().min(1, t("appointment.selectService")),
    resource: z.coerce.number<string | number>().min(1, t("appointment.selectSpecialist")),
    lead: z.coerce.number<string | number>().optional(),
    responsible_user: z.coerce.number<string | number>().optional(),
    date: z.string().min(1, t("appointment.dateRequired")),
    slot: z.string().optional(),
    source: z.string(),
    notes: z.string().optional(),
  });
}

type InputValues = z.input<ReturnType<typeof createSchema>>;
type Values = z.output<ReturnType<typeof createSchema>>;

function SetupNotice({
  title,
  description,
  to,
  action,
}: {
  title: string;
  description: string;
  to: string;
  action: string;
}) {
  return (
    <StatusNotice
      tone="warning"
      title={title}
      description={description}
      action={(
        <Link className="platforma-focus-ring inline-flex rounded-control px-2 py-1 font-semibold text-platforma-warning underline-offset-4 hover:underline" to={to}>
          {action}
        </Link>
      )}
    />
  );
}

function timeToMinutes(value: string) {
  const [hours, minutes] = value.split(":").map(Number);
  return hours * 60 + minutes;
}

function getSelectedWorkingHours(rows: WorkingHours[], weekday: number, resourceId: Id | null) {
  const resourceHours = resourceId ? rows.find((row) => row.resource === resourceId && row.weekday === weekday) : null;
  return resourceHours || rows.find((row) => !row.resource && row.weekday === weekday) || null;
}

function getNoSlotsReasonKey(hours: WorkingHours | null, durationMinutes: number) {
  if (!hours) return "appointment.noSlotsReasonMissingHours";
  if (hours.is_day_off) return "appointment.noSlotsReasonDayOff";
  if (timeToMinutes(hours.end_time) - timeToMinutes(hours.start_time) < durationMinutes) return "appointment.noSlotsReasonTooShort";
  return "appointment.noSlotsReasonBusy";
}

export function AppointmentForm({
  businessId,
  clients,
  services,
  resources,
  leads,
  initial,
  prefill,
  onSubmit,
  recordFirst = false,
  currency = "KZT",
  timeZone = "UTC",
}: {
  businessId: Id;
  clients: Client[];
  services: Service[];
  resources: Resource[];
  leads: Lead[];
  initial?: Appointment;
  recordFirst?: boolean;
  currency?: string;
  prefill?: {
    source_conversation?: Id | null;
    branch?: Id | null;
    client?: Id | null;
    service?: Id | null;
    resource?: Id | null;
    lead?: Id | null;
    date?: string;
    slot?: string;
    hour?: number;
    source?: Appointment["source"];
  };
  onSubmit: (payload: AppointmentCreatePayload) => Promise<unknown>;
  timeZone?: string;
}) {
  const { t, language } = useI18n();
  const { user } = useAuth();
  const members = useQuery({
    queryKey: ["team-members", "appointment", businessId, user?.id],
    queryFn: () => teamApi.allMembers(businessId),
    enabled: recordFirst && hasPermission(user, businessId, "team", "view"), retry: false,
  });
  const { getRecoverableMessage } = useActionFeedback();
  const branch = useBranchBooking(businessId, initial?.branch || prefill?.branch);
  const selectableServices = services.filter(
    (service) => ((service.is_active && !service.is_archived) && (!branch.enabled || branch.catalog?.offers.some((offer) => offer.service === service.id))) || service.id === initial?.service,
  ).map((service) => {
    const offer = branch.catalog?.offers.find((item) => item.service === service.id);
    return offer ? { ...service, duration_minutes: offer.duration_minutes, price_from: offer.price_from } : service;
  });
  const form = useForm<InputValues, unknown, Values>({
    resolver: zodResolver(createSchema(t)),
    defaultValues: {
      client: initial?.client || prefill?.client || (recordFirst ? 0 : clients[0]?.id) || 0,
      service: initial?.service || prefill?.service || selectableServices[0]?.id || 0,
      resource: initial?.resource || prefill?.resource || undefined,
      lead: initial?.lead || prefill?.lead || undefined,
      responsible_user: initial?.responsible_user || user?.id,
      date: initial?.start_at ? dateInTimeZone(initial.start_at, timeZone) : prefill?.date || todayInTimeZone(timeZone),
      slot: initial?.start_at || prefill?.slot || "",
      source: initial?.source || prefill?.source || "manual",
      notes: initial?.notes || "",
    },
  });

  const serviceId = form.watch("service");
  const resourceId = form.watch("resource");
  const date = form.watch("date");
  const skipSlotResetRef = useRef(true);
  const queryClient = useQueryClient();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const selectedService = selectableServices.find((service) => service.id === Number(serviceId));
  const hasClients = clients.length > 0;
  const hasServices = selectableServices.length > 0;
  const activeResources = resources.filter((resource) => resource.is_active && !resource.retired_at && resource.resource_type === "staff" && (!branch.enabled || branch.catalog?.assignments.some((item) => item.resource === resource.id && item.service_ids.includes(Number(serviceId)))));
  const hasResources = activeResources.length > 0;
  const locale = language === "en" ? "en-US" : language === "kk" ? "kk-KZ" : "ru-RU";
  const selectedDate = new Date(`${date}T00:00:00`);
  const selectedDateLabel = selectedDate.toLocaleDateString(locale, { weekday: "long", day: "2-digit", month: "long" });
  const selectedWeekday = (selectedDate.getDay() + 6) % 7;
  const quickHoursMutation = useMutation({
    mutationFn: () => workingHoursApi.applyPreset({ business: businessId, preset: "daily_9_20", resource: resourceId ? Number(resourceId) : "" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["working-hours"] });
      queryClient.invalidateQueries({ queryKey: ["available-slots"] });
      setSubmitError(null);
    },
    onError: (error) => setSubmitError(getRecoverableMessage(error)),
  });

  const slots = useQuery({
    queryKey: ["available-slots", businessId, serviceId, resourceId, date, branch.branchId],
    queryFn: () =>
      appointmentsApi.availableSlots({
        business_id: businessId,
        branch_id: branch.branchId ? Number(branch.branchId) : "",
        service_id: Number(serviceId),
        resource_id: resourceId ? Number(resourceId) : "",
        date,
      }),
    enabled: Boolean(branch.ready && businessId && serviceId && resourceId && date && !initial),
  });
  const noSlots = !initial && !slots.isLoading && slots.data?.length === 0;
  const workingHours = useQuery({
    queryKey: ["working-hours"],
    queryFn: workingHoursApi.list,
    enabled: Boolean(noSlots && !branch.enabled),
  });
  const dateExceptions = useQuery({
    queryKey: ["schedule-exceptions", businessId, resourceId, date],
    queryFn: () => scheduleExceptionsApi.list({ business: businessId, resource: resourceId, date }),
    enabled: Boolean(noSlots && !branch.enabled && resourceId && date),
  });
  const exception = dateExceptions.data?.[0];
  const selectedHours = noSlots ? (exception ? { ...exception, weekday: selectedWeekday } : getSelectedWorkingHours(workingHours.data || [], selectedWeekday, resourceId ? Number(resourceId) : null)) : null;
  const noSlotsReasonKey = branch.enabled ? "branches.noSlots" : getNoSlotsReasonKey(selectedHours, selectedService?.duration_minutes || 30);

  useEffect(() => {
    if (initial || !branch.ready || !branch.enabled) return;
    if (!branch.catalog?.offers.some((offer) => offer.service === Number(serviceId))) form.setValue("service", 0);
    if (!branch.catalog?.assignments.some((item) => item.resource === Number(resourceId) && item.service_ids.includes(Number(serviceId)))) form.setValue("resource", 0);
  }, [branch.catalog, branch.ready, branch.enabled, serviceId, resourceId, form, initial]);

  useEffect(() => {
    if (!initial) {
      if (skipSlotResetRef.current) {
        skipSlotResetRef.current = false;
        return;
      }
      form.setValue("slot", "");
      setSubmitError(null);
    }
  }, [date, serviceId, resourceId, branch.branchId, initial, form]);

  useEffect(() => {
    if (initial || prefill?.hour == null || form.getValues("slot") || !slots.data?.length) return;
    const matchingSlot = slots.data.find((slot) => hourInTimeZone(slot.start_at, timeZone) === prefill.hour);
    if (matchingSlot) form.setValue("slot", matchingSlot.start_at, { shouldDirty: true, shouldValidate: true });
  }, [form, initial, prefill?.hour, slots.data, timeZone]);

  return (
    <form
      data-testid="appointment-form"
      className="grid gap-4 rounded-card border border-platforma-border bg-surface-card p-4 shadow-card sm:p-5"
      onSubmit={form.handleSubmit(async (values) => {
        setSubmitError(null);
        if (!initial && !branch.ready) { setSubmitError(t("branches.choose")); return; }
        const startAt = initial?.start_at || values.slot;
        if (!initial && !startAt) {
          form.setError("slot", { message: t("appointment.selectSlotError") });
          return;
        }
        const duration = selectedService?.duration_minutes || 30;
        const endAt = new Date(startAt || Date.now());
        endAt.setMinutes(endAt.getMinutes() + duration);
        try {
          await onSubmit({
            business: businessId,
            ...(!initial && branch.branchId ? { branch: Number(branch.branchId) } : {}),
            client: values.client,
            service: values.service,
            resource: values.resource || null,
            lead: values.lead || null,
            start_at: startAt,
            end_at: initial?.end_at || endAt.toISOString(),
            source: values.source as Appointment["source"],
            notes: values.notes || "",
            ...(recordFirst ? {
              responsible_user: values.responsible_user || user?.id,
              source_conversation: prefill?.source_conversation || undefined,
              expected_price: selectedService?.price_from ?? null,
              expected_duration_minutes: selectedService?.duration_minutes,
            } : {}),
          });
        } catch (error) {
          setSubmitError(getRecoverableMessage(error));
        }
      })}
    >
      {branch.error ? <ErrorState error={branch.error} /> : null}
      {branch.enabled && <Select label={t("branches.branch")} value={branch.branchId} disabled={!!initial} onChange={(event) => branch.setBranchId(event.target.value)} options={[{ value: "", label: t("branches.choose") }, ...branch.branches.map((item) => ({ value: item.id, label: `${item.name} · ${item.address}` }))]} />}
      {!recordFirst && !hasClients ? (
        <SetupNotice
          title={t("appointment.needClientTitle")}
          description={t("appointment.needClientText")}
          to="/app/clients"
          action={t("appointment.goClients")}
        />
      ) : null}
      {!hasServices ? (
        <SetupNotice
          title={t("appointment.needServiceTitle")}
          description={t("appointment.needServiceText")}
          to="/app/business/services"
          action={t("appointment.goServices")}
        />
      ) : null}
      {!hasResources ? (
        <div className="rounded-card border border-platforma-border bg-surface-muted p-4 text-sm text-platforma-subtle">
          <p className="font-semibold text-platforma-ink">{t("appointment.resourceHintTitle")}</p>
          <p className="mt-1 leading-6">{t("appointment.resourceHintText")}</p>
          <Link className="mt-3 inline-flex font-bold text-brand-700 underline-offset-4 hover:underline" to="/app/business/resources">
            {t("appointment.goResources")}
          </Link>
        </div>
      ) : null}
      <div className="grid gap-4 sm:grid-cols-2">
        {recordFirst ? prefill?.source_conversation ? (
          <Input label={t("appointment.client")} value={clients.find(client => client.id === Number(form.watch("client")))?.full_name || t("common.client")} readOnly />
        ) : (
          <ClientPicker businessId={businessId} value={String(form.watch("client") || "")}
            onChange={value => form.setValue("client", Number(value), { shouldValidate: true })}
            error={form.formState.errors.client?.message} />
        ) : <Select label={t("appointment.client")} error={form.formState.errors.client?.message} options={[{ value: 0, label: t("appointment.selectClient") }, ...clients.map((client) => ({ value: client.id, label: client.full_name }))]} {...form.register("client")} value={form.watch("client")} />}
        <Select label={t("appointment.service")} error={form.formState.errors.service?.message} options={[{ value: 0, label: t("appointment.selectService") }, ...selectableServices.map((service) => ({ value: service.id, label: `${service.name} · ${service.duration_minutes} ${t("appointment.minutes")}${recordFirst ? ` · ${formatMoney(service.price_from, currency)}` : ""}` }))]} {...form.register("service")} value={form.watch("service")} />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Select
          label={t("appointment.resource")}
          error={form.formState.errors.resource?.message}
          options={[
            { value: "", label: t("appointment.selectSpecialist") },
            ...activeResources.map((resource) => ({ value: resource.id, label: resource.name })),
          ]}
          {...form.register("resource")}
          value={form.watch("resource") || ""}
        />
        {recordFirst ? <Select label={t("appointment.responsible")} value={form.watch("responsible_user")}
          options={[{ value: user?.id || "", label: user?.full_name || user?.email || t("appointment.responsible") },
            ...(members.data || []).filter(member => member.is_active && member.user.id !== user?.id)
              .map(member => ({ value: member.user.id, label: member.user.full_name || member.user.email }))]}
          {...form.register("responsible_user")} /> :
          <Select label={t("appointment.lead")} options={[{ value: "", label: t("appointment.noLead") }, ...leads.map((lead) => ({ value: lead.id, label: `${t("appointment.lead")} #${lead.id}` }))]} {...form.register("lead")} />}
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Input label={t("appointment.date")} type="date" error={form.formState.errors.date?.message} {...form.register("date")} disabled={Boolean(initial)} />
        {initial ? (
          <Input label={t("appointment.time")} value={new Date(initial.start_at).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit", timeZone })} readOnly />
        ) : (
          <Select
            label={t("appointment.slot")}
            error={form.formState.errors.slot?.message}
            options={[
              {
                value: "",
                label: slots.isLoading
                  ? t("appointment.loadingSlots")
                  : slots.data?.length === 0
                    ? t("appointment.noSlots")
                    : t("appointment.selectTime"),
              },
              ...(slots.data || []).map((slot) => ({
                value: slot.start_at,
                label: new Date(slot.start_at).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit", timeZone }),
              })),
            ]}
            {...form.register("slot")}
          />
        )}
      </div>
      {slots.error ? (
        <ErrorState message={getRecoverableMessage(slots.error)} action={<Button type="button" onClick={() => void slots.refetch()}>{t("common.retry")}</Button>} />
      ) : null}
      {noSlots ? (
        <StatusNotice
          tone="warning"
          title={t("appointment.noSlotsForDate").replace("{date}", selectedDateLabel)}
          description={t(noSlotsReasonKey)}
          details={(
            <>
              {selectedHours && !selectedHours.is_day_off ? (
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-platforma-warning">
                  {t("appointment.workingWindow").replace("{start}", selectedHours.start_time.slice(0, 5)).replace("{end}", selectedHours.end_time.slice(0, 5))}
                </p>
              ) : null}
              <div className="mt-3 flex flex-wrap gap-2">
                {!exception && !branch.enabled ? <Button type="button" variant="secondary" isLoading={quickHoursMutation.isPending} onClick={() => quickHoursMutation.mutate()}>
                  {t("appointment.applyQuickHours")}
                </Button> : null}
                <Link className="platforma-focus-ring inline-flex min-h-10 items-center rounded-control px-4 py-2 font-semibold text-platforma-warning underline-offset-4 hover:underline" to={branch.enabled ? `/app/business/branches?branch=${branch.branchId}` : `/app/business/working-hours?view=resources&resource=${resourceId}&date=${date}`}>
                  {t("appointment.openHours")}
                </Link>
              </div>
            </>
          )}
        />
      ) : null}
      {submitError ? (
        <ErrorState message={submitError} action={recordFirst ? <Button type="button" onClick={() => {
          form.setValue("slot", "");
          void Promise.all(["services", "resources", "branch-catalog", "available-slots", "team-members"]
            .map(key => queryClient.invalidateQueries({ queryKey: [key] })));
        }}>{t("common.refresh")}</Button> : undefined} />
      ) : null}
      {recordFirst && members.error ? <ErrorState error={members.error} action={<Button type="button" onClick={() => void members.refetch()}>{t("common.retry")}</Button>} /> : null}
      {!recordFirst && <Select label={t("appointment.source")} options={[
        { value: "manual", label: t("appointment.sourceManual") },
        { value: "website", label: t("appointment.sourceWebsite") },
        { value: "telegram", label: "Telegram" },
        { value: "whatsapp", label: "WhatsApp" },
        { value: "instagram", label: "Instagram" },
        { value: "bot", label: "Bot" },
      ]} {...form.register("source")} />}
      <Textarea label={t("appointment.notes")} {...form.register("notes")} />
      <Button data-testid="appointment-submit" type="submit" isLoading={form.formState.isSubmitting} disabled={!initial && (!branch.ready || (!recordFirst && !hasClients) || !hasServices || slots.isLoading || slots.data?.length === 0)}>
        {initial ? t("appointment.save") : t("appointment.create")}
      </Button>
    </form>
  );
}
