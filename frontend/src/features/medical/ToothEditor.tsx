import { useEffect, useId, useImperativeHandle, useRef, useState, type Ref } from "react";
import axios from "axios";
import { medicalClinicalApi, type AppointmentClinicalContext } from "../../api/medicalClinical";
import { medicalToothApi, type ToothSurfaceOptions } from "../../api/medicalTooth";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Textarea } from "../../components/ui/Textarea";
import { Select } from "../../components/ui/Select";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { useUnsavedEntryWarning } from "../auth/useUnsavedEntryWarning";
import type { ClinicalDraftControl } from "./ClinicalDraftForm";

export function ToothEditor({ context, tooth, revisions, control, onSaved, onDenied, onReload }: {
  context: AppointmentClinicalContext; tooth: number; revisions: ReadonlyMap<string, number>; control: Ref<ClinicalDraftControl>;
  onSaved: () => void; onDenied: (cause: unknown) => void; onReload: () => void;
}) {
  const { t, language } = useI18n();
  const surfaceHelpId = useId();
  const [surface, setSurface] = useState("");
  const [options, setOptions] = useState<ToothSurfaceOptions | null>(null);
  const [optionsError, setOptionsError] = useState<unknown>(null);
  const [optionsAttempt, setOptionsAttempt] = useState(0);
  const [fresh, setFresh] = useState<AppointmentClinicalContext | null>(null);
  const [observation, setObservation] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const [pending, setPending] = useState(false);
  const [conflict, setConflict] = useState(false);
  const saving = useRef(false);
  const dirtyNow = useRef(false);
  const controller = useRef(new AbortController());
  const request = useRef<{ fingerprint: string; key: string } | null>(null);
  const dirty = Boolean(observation || reason);
  useUnsavedEntryWarning(dirty);
  useEffect(() => {
    const active = new AbortController();
    setOptions(null); setOptionsError(null);
    medicalToothApi.surfaceOptions({ business_id: context.business_id, patient_id: context.patient.id,
      appointment_id: context.appointment.id, tooth }, active.signal)
      .then(value => { if (!active.signal.aborted) setOptions(value); })
      .catch(cause => { if (!active.signal.aborted) {
        if (axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0)) onDenied(cause);
        else setOptionsError(cause);
      } });
    return () => active.abort();
  }, [context, tooth, optionsAttempt, onDenied]);
  useEffect(() => {
    const active = new AbortController(); controller.current = active;
    setFresh(null); setError(null);
    medicalClinicalApi.appointmentContext({ business_id: context.business_id, appointment_id: context.appointment.id }, active.signal)
      .then(value => { if (!active.signal.aborted) {
        if (value.patient.id !== context.patient.id) onDenied(new Error("The appointment patient changed. Reload the medical workspace."));
        else setFresh(value);
      } })
      .catch(cause => { if (!active.signal.aborted) {
        if (axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0)) onDenied(cause);
        else setError(cause);
      } });
    return () => active.abort();
  }, [context, attempt, onDenied]);
  useImperativeHandle(control, () => ({ save, isPending: () => saving.current, isDirty: () => dirtyNow.current }));
  async function save(): Promise<boolean> {
    if (saving.current || conflict || !fresh?.actions.save_draft || !fresh.encounter) return false;
    if (!dirtyNow.current) return true;
    if (!observation.trim()) return false;
    if (surface && (!options?.reference || !options.surfaces.some(item => item.code === surface))) return false;
    saving.current = true; setPending(true); setError(null);
    const payload = { business_id: fresh.business_id, patient_id: fresh.patient.id, encounter_id: fresh.encounter.id,
      tooth, expected_patient_revision: fresh.patient.revision, expected_encounter_revision: fresh.encounter.revision,
      expected_tooth_revision: revisions.get(surface) ?? 0, observation, reason,
      ...(surface ? { surface, surface_reference: options!.reference! } : {}) };
    const fingerprint = JSON.stringify(payload);
    if (request.current?.fingerprint !== fingerprint) request.current = { fingerprint, key: crypto.randomUUID() };
    const signal = controller.current.signal;
    try {
      await medicalToothApi.save(payload, request.current.key, signal);
      if (!signal.aborted) { dirtyNow.current = false; onSaved(); return true; }
    } catch (cause) {
      if (!signal.aborted) {
        const status = axios.isAxiosError(cause) ? cause.response?.status : undefined;
        if (status === 401 || status === 403) onDenied(cause);
        else { setError(cause); if (status === 409) setConflict(true); }
      }
    } finally { saving.current = false; if (!signal.aborted) setPending(false); }
    return false;
  }
  if (!fresh) return error ? <ErrorState message={getApiErrorMessage(error)} action={<Button size="lg" variant="secondary" onClick={() => setAttempt(x => x + 1)}>{t("common.retry")}</Button>} /> : <LoadingState />;
  if (!fresh.actions.save_draft || !fresh.encounter) return <p className="text-sm text-platforma-subtle">{t("medical.tooth.readOnly")}</p>;
  return <form autoComplete="off" className="space-y-4 border-t border-platforma-border pt-4" data-testid="tooth-editor" onSubmit={event => { event.preventDefault(); void save(); }}>
    <h3 className="font-medium">{t("medical.tooth.new")}</h3>
    <Select label={t("medical.tooth.surface")} value={surface} aria-describedby={dirty ? surfaceHelpId : undefined}
      disabled={!options || dirty || pending || conflict}
      options={[{ value: "", label: t("medical.tooth.whole") }, ...(options?.surfaces ?? []).map(item => ({ value: item.code, label: item.labels[language] || item.code }))]}
      onChange={event => { if (!dirtyNow.current && !saving.current && !conflict) setSurface(event.target.value); }} />
    {dirty ? <p id={surfaceHelpId} className="text-sm text-platforma-subtle">{t("medical.tooth.surfaceLocked")}</p> : null}
    {optionsError ? <ErrorState message={getApiErrorMessage(optionsError)} action={<Button type="button" size="lg" variant="secondary" onClick={() => setOptionsAttempt(x => x + 1)}>{t("common.retry")}</Button>} /> : !options ? <LoadingState /> : null}
    <Textarea label={t("medical.tooth.observation")} aria-label={t("medical.tooth.observation")} value={observation} maxLength={32768} required disabled={pending} readOnly={conflict}
      onChange={event => { dirtyNow.current = Boolean(event.target.value || reason); setObservation(event.target.value); }} />
    <Textarea label={t("medical.tooth.reason")} aria-label={t("medical.tooth.reason")} value={reason} maxLength={2000} disabled={pending} readOnly={conflict}
      onChange={event => { dirtyNow.current = Boolean(observation || event.target.value); setReason(event.target.value); }} />
    {error ? <ErrorState message={conflict ? t("medical.clinical.conflict") : getApiErrorMessage(error)} /> : null}
    {conflict ? <Button type="button" size="lg" variant="secondary" onClick={() => { if (!dirtyNow.current || window.confirm(t("medical.clinical.discard"))) onReload(); }}>{t("medical.clinical.reload")}</Button> : null}
    <Button type="submit" size="lg" isLoading={pending} disabled={!observation.trim() || conflict}>{t("medical.tooth.save")}</Button>
  </form>;
}
