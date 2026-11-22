import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { medicalPatientsApi, type PatientRegistration, type PatientScope, type PatientSearchKind } from "../../api/medicalPatients";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Textarea } from "../../components/ui/Textarea";
import { ErrorState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import type { RoleDraftState } from "./roles/MedicalRoleCommand";

export function PatientRegistrationForm({ scope, initialKind, initialQuery, hasMatches, guard, onCancel, onSaved, onDenied }: {
  scope: PatientScope; initialKind: PatientSearchKind; initialQuery: string; hasMatches: boolean;
  guard: { current: RoleDraftState }; onCancel: () => void; onSaved: (clientId: number) => void; onDenied: () => void;
}) {
  const { t } = useI18n();
  const initial = { full_name: initialKind === "name" ? initialQuery : "", phone: initialKind === "phone" ? initialQuery : "",
    email: initialKind === "email" ? initialQuery : "", birth: initialKind === "birth" ? initialQuery : "",
    iin: initialKind === "iin" ? initialQuery : "", sex: "", address: "" };
  const [values, setValues] = useState(initial);
  const [reviewMatches, setReviewMatches] = useState(hasMatches);
  const [confirmed, setConfirmed] = useState(false);
  const [pending, setPending] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const request = useRef<AbortController | null>(null);
  const retry = useRef<{ fingerprint: string; key: string } | null>(null);
  guard.current.dirty = confirmed || JSON.stringify(values) !== JSON.stringify(initial);
  useEffect(() => () => { request.current?.abort(); guard.current = { dirty: false, pending: false }; }, [guard]);
  async function submit() {
    if (request.current || conflict || (reviewMatches && !confirmed)) return;
    const payload: PatientRegistration = { ...scope, full_name: values.full_name, phone: values.phone, email: values.email,
      demographics: { ...(values.birth ? { date_of_birth: values.birth } : {}), ...(values.sex ? { sex: values.sex } : {}),
        ...(values.address ? { address: values.address } : {}) }, iin: values.iin || null, confirmed_separate_person: confirmed };
    const fingerprint = JSON.stringify(payload);
    if (retry.current?.fingerprint !== fingerprint) retry.current = { fingerprint, key: crypto.randomUUID() };
    const controller = new AbortController(); request.current = controller;
    guard.current.pending = true; setPending(true); setError(null);
    try {
      const result = await medicalPatientsApi.register(payload, retry.current.key, controller.signal);
      if (!controller.signal.aborted) { guard.current = { dirty: false, pending: false }; onSaved(result.client_id); }
    } catch (cause) {
      if (controller.signal.aborted) return;
      const status = axios.isAxiosError(cause) ? cause.response?.status : undefined;
      if (status === 401 || status === 403) onDenied();
      else if (axios.isAxiosError(cause) && cause.response?.data?.code === "patient_matches_require_review") {
        setReviewMatches(true); setConfirmed(false);
      } else { setError(cause); setConflict(status === 409); }
    } finally {
      request.current = null; guard.current.pending = false;
      if (!controller.signal.aborted) setPending(false);
    }
  }
  function cancel() {
    if (pending || (guard.current.dirty && !window.confirm(t("medical.clinical.discard")))) return;
    onCancel();
  }
  function change(key: keyof typeof values, value: string) { setValues(current => ({ ...current, [key]: value })); setConfirmed(false); }
  return <form className="space-y-4" autoComplete="off" onSubmit={event => { event.preventDefault(); void submit(); }} data-testid="patient-registration">
    <fieldset disabled={pending || conflict} className="min-w-0 space-y-4">
      <Input label={t("medical.fullName")} value={values.full_name} onChange={event => change("full_name", event.target.value)} required maxLength={255} />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Input label={t("medical.search.phone")} value={values.phone} onChange={event => change("phone", event.target.value)} type="tel" maxLength={32} />
        <Input label={t("medical.search.email")} value={values.email} onChange={event => change("email", event.target.value)} type="email" />
        <Input label={t("medical.birth")} value={values.birth} onChange={event => change("birth", event.target.value)} type="date" />
        <Input label={t("medical.sex")} value={values.sex} onChange={event => change("sex", event.target.value)} maxLength={32} />
      </div>
      <Textarea label={t("medical.address")} value={values.address} onChange={event => change("address", event.target.value)} maxLength={2000} />
      <Input label={t("medical.iin")} value={values.iin} onChange={event => change("iin", event.target.value)} inputMode="numeric" pattern="[0-9]{12}" maxLength={12} />
      {reviewMatches ? <div className="space-y-2">
        <p role="status" className="text-sm text-platforma-text">{t("medical.registration.matches")}</p>
        <label className="flex min-h-11 items-center gap-3 text-sm text-platforma-text">
          <input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} className="platforma-focus-ring h-5 w-5 shrink-0 accent-brand-600" />
          {t("medical.registration.separate")}
        </label>
      </div> : null}
    </fieldset>
    {error ? <ErrorState message={conflict ? t("medical.registration.conflict") : getApiErrorMessage(error)} /> : null}
    <div className="flex flex-wrap justify-end gap-2">
      <Button type="button" variant="secondary" size="lg" disabled={pending} onClick={cancel}>{t("common.cancel")}</Button>
      <Button type="submit" size="lg" isLoading={pending} disabled={conflict || (reviewMatches && !confirmed)}>{t("medical.registration.create")}</Button>
    </div>
  </form>;
}
