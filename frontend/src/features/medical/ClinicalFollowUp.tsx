import { useEffect, useImperativeHandle, useRef, useState, type Ref } from "react";
import axios from "axios";
import type { ClinicalPlanBookingAccess } from "../../api/medicalClinical";
import { medicalReceptionApi, type FollowUpOption, type ReceptionResult } from "../../api/medicalReception";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { ErrorState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { useUnsavedEntryWarning } from "../auth/useUnsavedEntryWarning";
import { FollowUpOptionPicker } from "./FollowUpOptionPicker";

export function ClinicalFollowUp({ access, onClose, closeControl }: { access: ClinicalPlanBookingAccess; onClose: () => void; closeControl?: Ref<{ close: () => void }> }) {
  const { t } = useI18n();
  const { context } = access;
  const scope = { business_id: context.business_id, patient_id: context.patient.id, encounter_id: context.encounter!.id };
  const [service, setService] = useState<FollowUpOption | null>(null);
  const [staff, setStaff] = useState<FollowUpOption | null>(null);
  const [from, setFrom] = useState("");
  const [until, setUntil] = useState("");
  const [duration, setDuration] = useState("");
  const [onsite, setOnsite] = useState(false);
  const [pending, setPending] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [conflict, setConflict] = useState(false);
  const [result, setResult] = useState<ReceptionResult | null>(null);
  const request = useRef<{ fingerprint: string; key: string } | null>(null);
  const inFlight = useRef(false);
  const controller = useRef(new AbortController());
  const title = useRef<HTMLHeadingElement>(null);
  useUnsavedEntryWarning(dirty);
  useEffect(() => {
    const active = new AbortController(); controller.current = active; title.current?.focus();
    return () => active.abort();
  }, []);
  function close() {
    if (!inFlight.current && (!dirty || window.confirm(t("medical.clinical.discard")))) onClose();
  }
  useImperativeHandle(closeControl, () => ({ close }));
  async function submit() {
    if (inFlight.current || conflict || !service || !staff) return;
    const payload = { ...scope, expected_revision: access.revision, service_id: service.id,
      preferred_resource_id: staff.id, recommended_from: from, recommended_until: until,
      duration_minutes: duration ? Number(duration) : null, patient_in_clinic: onsite };
    const fingerprint = JSON.stringify(payload);
    if (request.current?.fingerprint !== fingerprint) request.current = { fingerprint, key: crypto.randomUUID() };
    inFlight.current = true; setPending(true); setError(null);
    const signal = controller.current.signal;
    try {
      const saved = await medicalReceptionApi.create(payload, request.current.key, signal);
      if (!signal.aborted) { setResult(saved); setDirty(false); }
    } catch (cause) {
      if (!signal.aborted) {
        const status = axios.isAxiosError(cause) ? cause.response?.status : undefined;
        if (status === 401 || status === 403 || status === 404) access.onDenied(cause);
        else { setError(cause); if (status === 409) setConflict(true); }
      }
    } finally { inFlight.current = false; if (!signal.aborted) setPending(false); }
  }
  return <section className="space-y-4" data-testid="clinical-follow-up">
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-platforma-border pb-3">
      {!closeControl && <h2 ref={title} tabIndex={-1} className="text-base font-semibold">{t("medical.reception.request")}</h2>}
      <Button type="button" size="lg" variant="secondary" disabled={pending} onClick={close}>{t("common.back")}</Button>
    </div>
    {result ? <div className="space-y-2" role="status">
      <p>{t("medical.reception.sent")}</p>
      <p className="text-sm text-platforma-subtle">{t(`medical.reception.state.${result.state}`)}</p>
    </div> : <form autoComplete="off" className="space-y-4" onChange={() => setDirty(true)} onSubmit={event => { event.preventDefault(); void submit(); }}>
      <p className="text-sm text-platforma-subtle">{t("medical.reception.notBooking")}</p>
      <div className="grid min-w-0 gap-4 md:grid-cols-2">
        <FollowUpOptionPicker scope={scope} kind="service" value={service} onChange={(value, changed) => { setService(value); if (changed) setDirty(true); }} onDenied={access.onDenied} disabled={pending || conflict} />
        <FollowUpOptionPicker scope={scope} kind="staff" value={staff} onChange={(value, changed) => { setStaff(value); if (changed) setDirty(true); }} onDenied={access.onDenied} disabled={pending || conflict} />
        <Input type="date" label={t("medical.reception.from")} value={from} required disabled={pending || conflict}
          onChange={event => { setFrom(event.target.value); if (!until || until < event.target.value) setUntil(event.target.value); }} />
        <Input type="date" label={t("medical.reception.until")} value={until} min={from || undefined} required disabled={pending || conflict}
          onChange={event => setUntil(event.target.value)} />
        <Input type="number" label={t("medical.reception.duration")} value={duration} min={1} step={1} disabled={pending || conflict}
          onChange={event => setDuration(event.target.value)} />
        <label className="flex min-h-11 items-center gap-3 text-sm">
          <input type="checkbox" className="h-5 w-5 accent-platforma-primary" checked={onsite} disabled={pending || conflict}
            onChange={event => setOnsite(event.target.checked)} />{t("medical.reception.onsite")}
        </label>
      </div>
      {error ? <ErrorState message={conflict ? t("medical.clinical.conflict") : getApiErrorMessage(error)} /> : null}
      {conflict ? <Button type="button" size="lg" variant="secondary" onClick={() => {
        if (!dirty || window.confirm(t("medical.clinical.discard"))) access.onReload();
      }}>{t("medical.clinical.reload")}</Button> : <Button type="submit" size="lg" isLoading={pending}
        disabled={!service || !staff || !from || !until}>{t("medical.reception.send")}</Button>}
    </form>}
  </section>;
}
