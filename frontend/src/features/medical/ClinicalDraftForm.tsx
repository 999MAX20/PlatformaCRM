import { Fragment, useContext, useEffect, useImperativeHandle, useRef, useState, type Ref, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { ClinicalPageSlots } from "./clinicalPageSlots";
import axios from "axios";
import { clinicalFields, medicalClinicalApi, type AppointmentClinicalContext, type ClinicalContent } from "../../api/medicalClinical";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { ClinicalSectionInput } from "./ClinicalSectionInput";
import { EncounterCompletion } from "./EncounterCompletion";
import { ClinicalFollowUp } from "./ClinicalFollowUp";
import { ClinicalFollowUpResults } from "./ClinicalFollowUpResults";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { useUnsavedEntryWarning } from "../auth/useUnsavedEntryWarning";

export type ClinicalDraftControl = { save: () => Promise<boolean>; isPending: () => boolean; isDirty: () => boolean };

export function ClinicalDraftForm({ context, onDirty, onDenied, onReload, onCompleted, draftControl, view = "encounter", pageLayout = false, chart, interactionBlocked = false }: {
  pageLayout?: boolean; chart?: ReactNode; interactionBlocked?: boolean;
  view?: "encounter" | "plan"; onCompleted: () => void;
  draftControl: Ref<ClinicalDraftControl>;
  context: AppointmentClinicalContext; onDirty: (value: boolean) => void; onDenied: (cause: unknown) => void; onReload: () => void;
}) {
  const { t } = useI18n();
  const slots = useContext(ClinicalPageSlots);
  const form = useRef<HTMLFormElement & HTMLDivElement>(null);
  const FormRoot = pageLayout ? "div" : "form";
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
  const [followUp, setFollowUp] = useState(false);
  const [completion, setCompletion] = useState(false);
  const completionButton = useRef<HTMLButtonElement>(null);
  const followUpButton = useRef<HTMLButtonElement>(null);
  const saving = useRef(false);
  const dirtyNow = useRef(false);
  const request = useRef<{ fingerprint: string; key: string } | null>(null);
  const controller = useRef(new AbortController());
  const dirty = JSON.stringify(content) !== JSON.stringify(baseline);
  useUnsavedEntryWarning(dirty);
  useEffect(() => onDirty(dirty || followUp || completion || pending), [dirty, followUp, completion, pending, onDirty]);
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
  useImperativeHandle(draftControl, () => ({ save, isPending: () => saving.current || followUp || completion, isDirty: () => dirtyNow.current }));
  async function save(): Promise<boolean> {
    if (saving.current || followUp || conflict || interactionBlocked || !loaded || !context.actions.save_draft) return false;
    if (form.current) {
      const invalid = form.current.querySelector<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>("input:invalid, textarea:invalid, select:invalid");
      if (invalid) { const details = invalid.closest("details"); if (details) details.open = true; invalid.reportValidity(); return false; }
    }
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
  if (completion) return <EncounterCompletion context={context} onCompleted={onCompleted} onDenied={onDenied} onBack={() => {
    setCompletion(false); requestAnimationFrame(() => completionButton.current?.focus());
  }} />;
  if (followUp) return <ClinicalFollowUp access={{ context, revision, onReload, onDenied, unsaved: dirty }} onClose={() => {
    setFollowUp(false); requestAnimationFrame(() => followUpButton.current?.focus());
  }} />;
  const saveAction = context.actions.save_draft ? <Button type={pageLayout ? "button" : "submit"} onClick={pageLayout ? () => void save() : undefined} size="lg" isLoading={pending} disabled={!dirty || conflict || interactionBlocked}>{t("medical.clinical.save")}</Button> : null;
  const workflowActions = <>{context.actions.save_draft ? <Button ref={followUpButton} type="button" size="lg" variant="secondary"
        disabled={pending || dirty || conflict || interactionBlocked} title={dirty ? t("medical.plan.saveBeforeBooking") : undefined}
        onClick={() => setFollowUp(true)}>{t("medical.reception.request")}</Button> : null}
      {context.actions.save_draft && view === "encounter" ? <Button ref={completionButton} type="button" size="lg" variant="secondary"
        disabled={pending || dirty || conflict || interactionBlocked} onClick={() => setCompletion(true)}>{t("medical.completion.title")}</Button> : null}</>;
  return <FormRoot ref={form} autoComplete="off" className={pageLayout ? "appointment-clinical-form space-y-4" : "space-y-4"} onInvalidCapture={event => { const details = (event.target as HTMLElement).closest("details"); if (details) details.open = true; }} onSubmit={event => { if (event.target !== event.currentTarget) return; event.preventDefault(); void save(); }}>
    <div className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-3 border-b border-platforma-border bg-surface-card py-3">
      <h2 className="text-base font-semibold">{t(view === "plan" ? "medical.clinical.plan" : "medical.clinical.note")}</h2>
      {pageLayout && slots?.save ? createPortal(saveAction, slots.save) : saveAction}
      {pageLayout && slots?.completion ? createPortal(workflowActions, slots.completion) : workflowActions}
      {saved ? <p role="status" className="w-full text-sm">{t("common.saved")}</p> : null}
      {error ? <div className="w-full"><ErrorState message={conflict ? t("medical.clinical.conflict") : getApiErrorMessage(error)} /></div> : null}
      {conflict ? <Button type="button" size="lg" variant="secondary" onClick={() => {
        if (!dirty || window.confirm(t("medical.clinical.discard"))) onReload();
      }}>{t("medical.clinical.reload")}</Button> : null}
    </div>
    {!context.actions.save_draft ? <p role="status" className="text-sm text-platforma-subtle">{t("medical.clinical.readOnly")}</p> : null}
    {[...clinicalFields].sort((a, b) => pageLayout ? (["complaints", "procedures", "plan"].includes(a) ? 0 : 1) - (["complaints", "procedures", "plan"].includes(b) ? 0 : 1) : 0).filter(field => view !== "plan" || field === "plan").map(field => {
      const input = <ClinicalSectionInput compact={pageLayout} field={field} content={content}
      assistance={{scope:{business_id:context.business_id,patient_id:context.patient.id,encounter_id:context.encounter!.id,expected_revision:revision},onDenied}}
      bookingAccess={{ context, revision, onReload, onDenied, unsaved: dirty }}
      planAccess={{ scope: { business_id: context.business_id, patient_id: context.patient.id,
        encounter_id: context.encounter!.id, appointment_id: context.appointment.id }, onDenied }}
      disabled={pending} readOnly={!context.actions.save_draft || conflict}
      onChange={next => {
        dirtyNow.current = JSON.stringify(next) !== JSON.stringify(baseline);
        setContent(next); setSaved(false);
      }} />;
      const secondary = pageLayout && ["anamnesis", "allergies", "contraindications", "examination", "diagnosis", "epicrisis"].includes(field);
      return <Fragment key={field}>{secondary ? <details className="appointment-secondary-field"><summary>{t(`medical.clinical.${field}`)}{content[field] ? <span>{content[field]}</span> : null}</summary>{input}</details> : input}
        {field === "complaints" && view === "encounter" ? chart : null}</Fragment>;
    })}
    {context.actions.save_draft ? <ClinicalFollowUpResults scope={{ business_id: context.business_id,
      patient_id: context.patient.id, encounter_id: context.encounter!.id }} onDenied={onDenied} unsaved={dirty || pending} /> : null}
  </FormRoot>;
}
