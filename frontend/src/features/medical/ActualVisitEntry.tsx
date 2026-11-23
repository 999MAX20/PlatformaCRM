import { useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import axios from "axios";
import { medicalActualVisitsApi as api, type ActualVisitContext, type ActualVisitScope, type ActualVisitResult } from "../../api/medicalActualVisits";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { Modal } from "../../components/ui/Modal";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useBranchBooking } from "../../hooks/useBranchBooking";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { dateInTimeZone } from "../../lib/format";
import { refreshAppointmentQueries } from "../../lib/appointmentCache";
import { useUnsavedEntryWarning } from "../auth/useUnsavedEntryWarning";
import { taskDateInput, taskDateISO } from "../tasks/workspaceUtils";
import { medicalRoleDenied } from "./roles/useMedicalRolePage";

const allowOpen = async () => true;
const ignoreOpenChange = () => {};

export function ActualVisitEntry({ scope, beforeOpen = allowOpen, onOpenChange = ignoreOpenChange }: {
  scope: ActualVisitScope; beforeOpen?: () => Promise<boolean>; onOpenChange?: (open: boolean) => void;
}) {
  const { t } = useI18n();
  const [context, setContext] = useState<ActualVisitContext | null>(null);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setContext(null); setError(null);
    api.context(scope, controller.signal).then(value => { if (!controller.signal.aborted) setContext(value); })
      .catch(cause => { if (!controller.signal.aborted && !medicalRoleDenied(cause) && !(axios.isAxiosError(cause) && cause.response?.status === 404)) setError(cause); });
    return () => controller.abort();
  }, [scope.business_id, scope.client_id, scope.branch_id, attempt]);
  useEffect(() => () => onOpenChange(false), [onOpenChange]);
  const close = () => { setOpen(false); onOpenChange(false); setAttempt(n => n + 1); };
  if (error) return <ErrorState message={getApiErrorMessage(error)} action={<Button size="lg" variant="secondary" onClick={() => setAttempt(n => n + 1)}>{t("common.retry")}</Button>} />;
  if (!context) return null;
  return <>
    <Button type="button" size="lg" variant="secondary" data-focus-return-id="medical-actual-visit" onClick={() => void (async () => {
      if (await beforeOpen()) { setOpen(true); onOpenChange(true); }
    })()}>{t("medical.actual.title")}</Button>
    {open ? <ActualVisitDialog scope={scope} initial={context} onClose={close} /> : null}
  </>;
}

function ActualVisitDialog({ scope, initial, onClose }: { scope: ActualVisitScope; initial: ActualVisitContext; onClose: () => void }) {
  const { t } = useI18n();
  const { business } = useActiveBusiness();
  const cache = useQueryClient();
  const navigate = useNavigate();
  const zone = business?.timezone || "UTC";
  const branch = useBranchBooking(scope.business_id, scope.branch_id);
  const [context, setContext] = useState(initial);
  const [serviceId, setServiceId] = useState("");
  const [resourceId, setResourceId] = useState("");
  const [start, setStart] = useState(taskDateInput(initial.now, zone));
  const [reason, setReason] = useState("");
  const [dirty, setDirty] = useState(false);
  const [pending, setPending] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [denied, setDenied] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [result, setResult] = useState<ActualVisitResult | null>(null);
  const busy = useRef(false);
  const request = useRef<{ fingerprint: string; key: string } | null>(null);
  const controller = useRef(new AbortController());
  useEffect(() => { const active = new AbortController(); controller.current = active; return () => active.abort(); }, []);
  useUnsavedEntryWarning(dirty && !result);
  const services = (branch.catalog?.offers || []).filter(item => item.is_active);
  const service = services.find(item => String(item.service) === serviceId);
  const offer = service;
  const resources = (branch.catalog?.assignments || []).filter(item => item.is_active &&
    context.resource_ids.includes(item.resource) && item.service_ids.includes(Number(serviceId)));
  const validResource = resources.some(item => String(item.resource) === resourceId);
  const earlier = start.slice(0, 10) < dateInTimeZone(context.now, zone);
  const close = () => { if (!busy.current && (!dirty || result || window.confirm(t("medical.clinical.discard")))) onClose(); };
  async function reload() {
    if (busy.current) return;
    setError(null);
    try { setContext(await api.context(scope, controller.current.signal)); setConflict(false); branch.retry(); }
    catch (cause) { setError(cause); if (medicalRoleDenied(cause)) setDenied(true); }
  }
  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (busy.current || !service || !offer || !validResource || conflict || denied) return;
    let startAt: string | null;
    try { startAt = taskDateISO(start, zone); } catch { setError(new Error(t("medical.actual.invalidTime"))); return; }
    if (!startAt) return;
    const payload = { ...scope, service_id: service.service, resource_id: Number(resourceId), start_at: startAt,
      expected_patient_revision: context.patient_revision, expected_price: offer.price_from,
      expected_duration_minutes: offer.duration_minutes, reason };
    const fingerprint = JSON.stringify(payload);
    if (request.current?.fingerprint !== fingerprint) request.current = { fingerprint, key: crypto.randomUUID() };
    busy.current = true; setPending(true); setError(null);
    try {
      const value = await api.create(payload, request.current.key, controller.current.signal);
      if (!controller.current.signal.aborted) { setResult(value); setDirty(false); void refreshAppointmentQueries(cache); }
    } catch (cause) {
      if (!controller.current.signal.aborted) {
        setError(cause);
        if (medicalRoleDenied(cause)) setDenied(true);
        else if (axios.isAxiosError(cause) && cause.response?.status === 409) setConflict(true);
      }
    } finally { busy.current = false; if (!controller.current.signal.aborted) setPending(false); }
  }
  const loadError = branch.error;
  return <Modal open title={t("medical.actual.title")} size="lg" closeOnBackdrop={false} onClose={close} focusReturnId="medical-actual-visit" testId="medical-actual-visit">
    {result ? <div className="space-y-4"><p role="status">{t("medical.actual.saved")}</p><div className="flex flex-wrap gap-2">
      <Button size="lg" onClick={() => { flushSync(onClose); navigate(`/app/calendar?appointment=${result.id}&date=${dateInTimeZone(result.start_at, zone)}&view=day`); }}>{t("medical.plan.openBooking")}</Button>
      <Button size="lg" variant="secondary" onClick={close}>{t("common.close")}</Button></div></div> : denied ? <ErrorState message={t("medical.denied")} /> :
      loadError ? <ErrorState message={getApiErrorMessage(loadError)} action={<Button onClick={() => void reload()}>{t("common.retry")}</Button>} /> :
        branch.loading ? <LoadingState /> :
          <form onSubmit={event => void save(event)} className="min-w-0 space-y-4">
            <fieldset disabled={pending} className="min-w-0 space-y-4">
              <Select label={t("appointment.service")} value={serviceId} options={[{ value: "", label: t("appointment.selectService") }, ...services.map(item => ({ value: item.service, label: item.service_name }))]}
                onChange={event => { setServiceId(event.target.value); setResourceId(""); setDirty(true); }} />
              <Select label={t("appointment.resource")} value={resourceId} options={[{ value: "", label: t("appointment.selectSpecialist") }, ...resources.map(item => ({ value: item.resource, label: item.resource_name }))]}
                onChange={event => { setResourceId(event.target.value); setDirty(true); }} />
              <Input label={t("medical.actual.start")} type="datetime-local" value={start} required
                min={context.earlier_allowed ? undefined : `${dateInTimeZone(context.now, zone)}T00:00`}
                max={taskDateInput(new Date().toISOString(), zone)} onChange={event => { setStart(event.target.value); setDirty(true); }} />
              <p className="text-sm text-platforma-subtle">{t("medical.actual.zone", { zone })}</p>
              <Textarea label={t("medical.actual.reason")} value={reason} required={earlier} maxLength={2000} onChange={event => { setReason(event.target.value); setDirty(true); }} />
            </fieldset>
            {error ? <ErrorState message={conflict ? t("medical.actual.conflict") : getApiErrorMessage(error)} /> : null}
            <div className="flex flex-wrap gap-2"><Button type="submit" size="lg" isLoading={pending} disabled={!service || !validResource || conflict}>{t("medical.actual.confirm")}</Button>
              <Button type="button" size="lg" variant="secondary" disabled={pending} onClick={close}>{t("common.cancel")}</Button>
              {conflict ? <Button type="button" size="lg" variant="secondary" disabled={pending} onClick={() => void reload()}>{t("medical.clinical.reload")}</Button> : null}</div>
          </form>}
  </Modal>;
}
