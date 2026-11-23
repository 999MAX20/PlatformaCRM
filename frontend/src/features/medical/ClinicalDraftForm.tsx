import { useEffect, useImperativeHandle, useRef, useState, type Ref } from "react";
import axios from "axios";
import { clinicalFields, medicalClinicalApi, type AppointmentClinicalContext, type ClinicalContent } from "../../api/medicalClinical";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { ClinicalSectionInput } from "./ClinicalSectionInput";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { useUnsavedEntryWarning } from "../auth/useUnsavedEntryWarning";

export type ClinicalDraftControl = { save: () => Promise<boolean>; isPending: () => boolean; isDirty: () => boolean };

export function ClinicalDraftForm({ context, onDirty, onDenied, onReload, draftControl }: {
  draftControl: Ref<ClinicalDraftControl>;
  context: AppointmentClinicalContext; onDirty: (value: boolean) => void; onDenied: (cause: unknown) => void; onReload: () => void;
}) {
  const { t } = useI18n();
  const form = useRef<HTMLFormElement>(null);
  const [content, setContent] = useState<ClinicalContent>({});
  const [baseline, setBaseline] = useState<ClinicalContent>({});
  const [revision, setRevision] = useState(context.encounter!.revision);
  const [loading, setLoading] = useState(true);
  const [loaded, setLoaded] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [refresh, setRefresh] = useState(0);
  const [saved, setSaved] = useState(false);
  const [conflict, setConflict] = useState(false);
  const saving = useRef(false);
  const dirtyNow = useRef(false);
  const request = useRef<{ fingerprint: string; key: string } | null>(null);
  const controller = useRef(new AbortController());
  const dirty = JSON.stringify(content) !== JSON.stringify(baseline);
  useUnsavedEntryWarning(dirty);
  useEffect(() => onDirty(dirty), [dirty, onDirty]);
  useEffect(() => {
    const active = new AbortController(); controller.current = active;
    setLoading(true); setError(null);
    medicalClinicalApi.version(context.encounter!.version_id, { business_id: context.business_id,
      patient_id: context.patient.id, appointment_id: context.appointment.id }, active.signal)
      .then(value => { if (!active.signal.aborted) { dirtyNow.current = false; setContent(value.content); setBaseline(value.content); setRevision(value.revision); setConflict(false); setLoaded(true); } })
      .catch(cause => { if (!active.signal.aborted) {
        if (axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0)) onDenied(cause);
        else setError(cause);
      } })
      .finally(() => { if (!active.signal.aborted) setLoading(false); });
    return () => active.abort();
  }, [context, refresh]); // Context changes remount the clinical scope through the parent.
  useImperativeHandle(draftControl, () => ({ save, isPending: () => saving.current, isDirty: () => dirtyNow.current }));
  async function save(): Promise<boolean> {
    if (saving.current || conflict || !loaded || !context.actions.save_draft) return false;
    if (form.current && !form.current.reportValidity()) return false;
    if (!dirty) return true;
    saving.current = true;
    const payload = { business_id: context.business_id, patient_id: context.patient.id, expected_revision: revision, content };
    const fingerprint = JSON.stringify(payload);
    if (request.current?.fingerprint !== fingerprint) request.current = { fingerprint, key: crypto.randomUUID() };
    setPending(true); setError(null); setSaved(false);
    const signal = controller.current.signal;
    try {
      const result = await medicalClinicalApi.saveDraft(context.encounter!.id, payload, request.current.key, signal);
      if (!signal.aborted) { dirtyNow.current = false; setRevision(result.revision); setBaseline(content); setSaved(true); request.current = null; return true; }
    } catch (cause) {
      if (!signal.aborted) {
        const status = axios.isAxiosError(cause) ? cause.response?.status : undefined;
        if (status === 401 || status === 403) onDenied(cause);
        else { setError(cause); if (status === 409) setConflict(true); }
      }
    } finally { saving.current = false; if (!signal.aborted) setPending(false); }
    return false;
  }
  if (loading) return <LoadingState />;
  if (!loaded) return <ErrorState message={getApiErrorMessage(error)} action={<Button size="lg" variant="secondary" onClick={() => setRefresh(value => value + 1)}>{t("common.retry")}</Button>} />;
  return <form ref={form} autoComplete="off" className="space-y-4" onSubmit={event => { event.preventDefault(); void save(); }}>
    <h2 className="text-base font-semibold">{t("medical.clinical.note")}</h2>
    {!context.actions.save_draft ? <p role="status" className="text-sm text-platforma-subtle">{t("medical.clinical.readOnly")}</p> : null}
    {clinicalFields.map(field => <ClinicalSectionInput key={field} field={field} content={content}
      disabled={pending} readOnly={!context.actions.save_draft || conflict}
      onChange={next => {
        dirtyNow.current = JSON.stringify(next) !== JSON.stringify(baseline);
        setContent(next); setSaved(false);
      }} />)}
    {error ? <ErrorState message={conflict ? t("medical.clinical.conflict") : getApiErrorMessage(error)} /> : null}
    {conflict ? <Button type="button" size="lg" variant="secondary" onClick={() => {
      if (!dirty || window.confirm(t("medical.clinical.discard"))) onReload();
    }}>{t("medical.clinical.reload")}</Button> : null}
    {saved ? <p role="status" className="text-sm">{t("common.saved")}</p> : null}
    {context.actions.save_draft ? <Button type="submit" size="lg" isLoading={pending} disabled={!dirty || conflict}>{t("medical.clinical.save")}</Button> : null}
  </form>;
}
