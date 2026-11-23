import axios from "axios";
import { useEffect, useRef, useState } from "react";
import { medicalClinicalApi, type AppointmentClinicalContext, type EncounterCompletion as Completion } from "../../api/medicalClinical";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { medicalRoleDenied } from "./roles/useMedicalRolePage";

export function EncounterCompletion({ context, onBack, onCompleted, onDenied }: {
  context: AppointmentClinicalContext; onBack: () => void; onCompleted: () => void; onDenied: (cause: unknown) => void;
}) {
  const { t } = useI18n();
  const [value, setValue] = useState<Completion | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [reason, setReason] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [pending, setPending] = useState(false);
  const [conflict, setConflict] = useState(false);
  const busy = useRef(false);
  const request = useRef<{ fingerprint: string; key: string } | null>(null);
  const controller = useRef(new AbortController());
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, []);
  useEffect(() => {
    const active = new AbortController(); controller.current = active;
    setValue(null); setError(null); setConflict(false);
    medicalClinicalApi.completion(context.encounter!.id, { business_id: context.business_id, patient_id: context.patient.id }, active.signal)
      .then(data => { if (!active.signal.aborted) setValue(data); })
      .catch(cause => { if (!active.signal.aborted) { if (medicalRoleDenied(cause)) onDenied(cause); else setError(cause); } });
    return () => active.abort();
  }, [context, attempt, onDenied]);
  async function complete(event: React.FormEvent) {
    event.preventDefault();
    if (!value?.ready || busy.current || conflict) return;
    const payload = { business_id: context.business_id, patient_id: context.patient.id,
      expected_revision: value.revision, expected_appointment_updated_at: value.appointment_updated_at, reason };
    const fingerprint = JSON.stringify(payload);
    if (request.current?.fingerprint !== fingerprint) request.current = { fingerprint, key: crypto.randomUUID() };
    busy.current = true; setPending(true); setError(null);
    const signal = controller.current.signal;
    try {
      await medicalClinicalApi.complete(context.encounter!.id, payload, request.current.key, signal);
      if (!signal.aborted) onCompleted();
    } catch (cause) {
      if (!signal.aborted) {
        if (medicalRoleDenied(cause)) onDenied(cause);
        else { setError(cause); if (axios.isAxiosError(cause) && cause.response?.status === 409) setConflict(true); }
      }
    } finally { busy.current = false; if (!signal.aborted) setPending(false); }
  }
  return <section className="min-w-0 space-y-4" data-testid="encounter-completion">
    <h2 ref={heading} tabIndex={-1} className="text-base font-semibold">{t("medical.completion.title")}</h2>
    {error ? <ErrorState message={conflict ? t("medical.clinical.conflict") : getApiErrorMessage(error)} /> : null}
    {!value && !error ? <LoadingState /> : null}
    {value ? <>
      <p className="text-sm">{t(value.ready ? "medical.completion.ready" : "medical.completion.missing")}</p>
      {value.missing_fields.length ? <ul className="list-disc space-y-2 pl-5 text-sm">{value.missing_fields.map(field => <li key={field}>{t(`medical.clinical.${field}`)}</li>)}</ul> : null}
      {value.documents.length ? <ul className="space-y-2 text-sm">{value.documents.map(document => <li key={`${document.kind_id}:${document.version_id}`} className="break-words">
        <span className="font-medium">{document.name}</span> — {t(document.ready ? "medical.completion.documentReady" : "medical.completion.documentMissing")}
      </li>)}</ul> : null}
      {value.ready ? <form onSubmit={event => void complete(event)} className="space-y-4">
        {value.early ? <Input label={t("medical.completion.earlyReason")} value={reason} required maxLength={500} disabled={pending || conflict}
          onChange={event => setReason(event.target.value)} /> : null}
        <Button type="submit" size="lg" isLoading={pending} disabled={conflict || value.early && !reason.trim()}>{t("medical.completion.confirm")}</Button>
      </form> : null}
    </> : null}
    <div className="flex flex-wrap gap-2">
      <Button type="button" size="lg" variant="secondary" disabled={pending} onClick={onBack}>{t("medical.completion.back")}</Button>
      <Button type="button" size="lg" variant="secondary" disabled={pending} onClick={() => setAttempt(n => n + 1)}>{t("medical.clinical.reload")}</Button>
    </div>
  </section>;
}
