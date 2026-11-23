import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import axios from "axios";
import { clientsApi } from "../../api/clients";
import type { AppointmentCreatePayload } from "../../api/appointments";
import { medicalClinicalApi, type ClinicalBookingRequest, type ClinicalBookingResult, type ClinicalContent, type ClinicalPlanBookingAccess } from "../../api/medicalClinical";
import { visitPlansApi, type VisitPlan } from "../../api/visitPlans";
import { getApiErrorMessage } from "../../api/client";
import type { Client } from "../../types";
import { AppointmentForm } from "../../components/forms/AppointmentForm";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useAuth } from "../auth/AuthProvider";
import { useUnsavedEntryWarning } from "../auth/useUnsavedEntryWarning";
import { useCalendarCatalog } from "../calendar/useCalendarCatalog";
import { hasPermission } from "../../lib/permissions";
import { refreshAppointmentQueries } from "../../lib/appointmentCache";
import { dateInTimeZone } from "../../lib/format";
import { useI18n } from "../../lib/i18n";

type Step = NonNullable<ClinicalContent["plan_steps"]>[number];
export function ClinicalPlanBooking({ step, access, disabled }: { step: Step; access: ClinicalPlanBookingAccess; disabled: boolean }) {
  const { t } = useI18n();
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  if (!hasPermission(user, access.context.business_id, "appointments", "create") ||
      !hasPermission(user, access.context.business_id, "appointments", "update")) return null;
  return <>
    <Button type="button" size="lg" variant="secondary" disabled={disabled || access.unsaved}
      title={access.unsaved ? t("medical.plan.saveBeforeBooking") : undefined}
      data-focus-return-id={`clinical-book-${step.id}`} onClick={() => setOpen(true)}>{t("medical.plan.book")}</Button>
    {open ? <BookingDialog step={step} access={access} onClose={() => setOpen(false)} /> : null}
  </>;
}

function BookingDialog({ step, access, onClose }: { step: Step; access: ClinicalPlanBookingAccess; onClose: () => void }) {
  const { t } = useI18n();
  const { user } = useAuth();
  const { business } = useActiveBusiness();
  const cache = useQueryClient();
  const navigate = useNavigate();
  const context = access.context;
  const catalog = useCalendarCatalog(context.business_id, user?.id, false, false);
  const [loaded, setLoaded] = useState<{ client: Client; plan: VisitPlan | null } | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const [dirty, setDirty] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [result, setResult] = useState<(ClinicalBookingResult & { startAt: string }) | null>(null);
  const pending = useRef(false);
  const request = useRef<{ fingerprint: string; key: string } | null>(null);
  const controller = useRef(new AbortController());
  useUnsavedEntryWarning(dirty);
  useEffect(() => {
    const active = new AbortController(); controller.current = active;
    setLoaded(null); setError(null);
    Promise.all([clientsApi.get(context.patient.client_id), step.visit_step ? visitPlansApi.get(context.business_id, step.visit_step.plan_id) : Promise.resolve(null)])
      .then(([client, plan]) => { if (!active.signal.aborted) {
        if (client.business !== context.business_id || (plan && plan.client !== context.patient.client_id)) access.onDenied(new Error("Clinical booking scope changed."));
        else setLoaded({ client, plan });
      } }).catch(cause => { if (!active.signal.aborted) {
        if (axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0)) access.onDenied(cause);
        else setError(cause);
      } });
    return () => active.abort();
  }, [context.business_id, context.patient.client_id, step.visit_step?.plan_id, attempt]);
  const linked = loaded?.plan?.steps.find(item => item.id === step.visit_step?.id);
  const unavailable = Boolean(step.visit_step && loaded && (!linked || linked.removed_at || linked.appointment || loaded.plan?.is_archived || loaded.plan?.terminated_at));
  const catalogError = catalog.services.error || catalog.resources.error;
  function close() {
    if (pending.current || (dirty && !result && !window.confirm(t("medical.clinical.discard")))) return;
    onClose();
    if (result) access.onReload();
  }
  async function book(payload: AppointmentCreatePayload) {
    if (!loaded || pending.current || unavailable) return;
    if (conflict) throw new Error(t("medical.plan.reviewBooking"));
    if (payload.client !== context.patient.client_id || !payload.service || !payload.resource || !payload.branch ||
        !payload.start_at || !payload.expected_duration_minutes || payload.expected_price === undefined) {
      throw new Error(t("medical.plan.reviewBooking"));
    }
    if (!window.confirm(t("medical.plan.confirmBooking"))) return;
    const command: ClinicalBookingRequest = { business_id: context.business_id, patient_id: context.patient.id,
      expected_revision: access.revision, step_id: step.id, service_id: payload.service, resource_id: payload.resource,
      branch_id: payload.branch, responsible_user_id: payload.responsible_user ?? undefined,
      ...(loaded.plan ? { expected_plan_revision: loaded.plan.revision } : {}), start_at: payload.start_at,
      expected_price: payload.expected_price, expected_duration_minutes: payload.expected_duration_minutes,
      confirmed: true, notes: payload.notes || "" };
    const fingerprint = JSON.stringify(command);
    if (request.current?.fingerprint !== fingerprint) request.current = { fingerprint, key: crypto.randomUUID() };
    pending.current = true;
    try {
      const saved = await medicalClinicalApi.bookPlanStep(context.encounter!.id, command, request.current.key, controller.current.signal);
      if (!controller.current.signal.aborted) {
        setResult({ ...saved, startAt: command.start_at }); setDirty(false);
        void refreshAppointmentQueries(cache);
      }
    } catch (cause) {
      if (!controller.current.signal.aborted) {
        const status = axios.isAxiosError(cause) ? cause.response?.status : undefined;
        if (status === 401 || status === 403) access.onDenied(cause);
        else if (status === 409) setConflict(true);
      }
      throw cause;
    } finally { pending.current = false; }
  }
  return <Modal open onClose={close} closeOnBackdrop={false} size="lg" title={t("medical.plan.book")}
    focusReturnId={`clinical-book-${step.id}`} testId="clinical-plan-booking">
    <div className="space-y-4">
      {result ? <>
        <p role="status">{t("medical.plan.booked")}</p>
        <div className="flex flex-wrap gap-2"><Button size="lg" onClick={() => navigate(`/app/calendar?appointment=${result.appointment_id}&date=${dateInTimeZone(result.startAt, business?.timezone || "UTC")}`)}>{t("medical.plan.openBooking")}</Button>
          <Button size="lg" variant="secondary" onClick={close}>{t("common.close")}</Button></div>
      </> : error || catalogError ? <ErrorState message={getApiErrorMessage(error || catalogError)} action={<Button size="lg" variant="secondary" onClick={() => {
        setAttempt(value => value + 1); void catalog.services.refetch(); void catalog.resources.refetch();
      }}>{t("common.retry")}</Button>} /> : !loaded || catalog.services.isPending || catalog.resources.isPending ? <LoadingState /> :
        unavailable || business?.id !== context.business_id ? <p role="alert">{t("medical.plan.reviewBooking")}</p> : <>
          <AppointmentForm businessId={context.business_id} clients={[loaded.client]} services={catalog.services.data || []}
            resources={catalog.resources.data || []} leads={[]} recordFirst fixedClient fixedContext={Boolean(linked)}
            currency={business.currency} timeZone={business.timezone} onDirtyChange={setDirty} onSubmit={book}
            prefill={{ client: context.patient.client_id, branch: linked?.branch || context.appointment.branch_id,
              service: linked?.service, resource: linked?.resource, responsible_user: linked?.responsible_user || loaded.plan?.responsible_user || user?.id }} />
          {conflict ? <Button size="lg" variant="secondary" onClick={() => {
            if (!dirty || window.confirm(t("medical.clinical.discard"))) { onClose(); access.onReload(); }
          }}>{t("medical.clinical.reload")}</Button> : null}
        </>}
    </div>
  </Modal>;
}
