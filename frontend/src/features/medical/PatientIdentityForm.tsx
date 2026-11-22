import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { medicalPatientsApi, type PatientAdministration, type PatientScope, type PatientVerificationForm } from "../../api/medicalPatients";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";

export type PatientEditMode = "create" | "preliminary" | "verify" | "correct";

export function PatientIdentityForm({ mode, patient, clientId, clientName, scope, onSaved, onDenied, onCancel }: {
  mode: PatientEditMode; patient: PatientAdministration | null; clientId: number; clientName: string; scope: PatientScope;
  onSaved: () => void; onDenied: () => void; onCancel: () => void;
}) {
  const { t, language } = useI18n();
  const [name, setName] = useState(patient?.full_name ?? "");
  const [birth, setBirth] = useState(patient?.demographics.date_of_birth ?? "");
  const [sex, setSex] = useState(patient?.demographics.sex ?? "");
  const [address, setAddress] = useState(patient?.demographics.address ?? "");
  const [iin, setIin] = useState(patient?.iin ?? "");
  const [reason, setReason] = useState("");
  const [protocol, setProtocol] = useState<PatientVerificationForm | null>(null);
  const [method, setMethod] = useState("");
  const [fields, setFields] = useState<Record<string, string>>({});
  const [protocolError, setProtocolError] = useState<unknown>(null);
  const [error, setError] = useState<unknown>(null);
  const [conflict, setConflict] = useState(false);
  const [pending, setPending] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const request = useRef<AbortController | null>(null);
  const lastCommand = useRef<{ payload: string; key: string } | null>(null);
  const needsProtocol = mode === "verify" || mode === "correct";
  const selectedMethod = protocol?.methods.find(item => item.code === method);

  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    if (!needsProtocol) return;
    const controller = new AbortController();
    setProtocolError(null);
    medicalPatientsApi.verificationForm(scope, controller.signal).then(data => {
      setProtocol(data);
      setMethod(data.methods[0]?.code ?? "");
    }).catch(cause => {
      if (controller.signal.aborted) return;
      if (axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0)) onDenied();
      else setProtocolError(cause);
    });
    return () => controller.abort();
  }, [scope.business_id, scope.branch_id, needsProtocol, attempt]);

  async function submit() {
    if (request.current || conflict) return;
    const demographics = { ...(birth ? { date_of_birth: birth } : {}), ...(sex ? { sex } : {}), ...(address ? { address } : {}) };
    const payload = mode === "create" ? { ...scope, client_id: clientId, demographics, iin: iin || null }
      : mode === "preliminary" ? { ...scope, expected_revision: patient!.revision, demographics, iin: iin || null, reason }
      : { ...scope, expected_revision: patient!.revision, expected_client_updated_at: patient!.client_updated_at,
        protocol_reference: protocol!.reference, method, fields,
        ...(mode === "correct" ? { full_name: name, demographics, reason } : {}) };
    const fingerprint = JSON.stringify(payload);
    if (lastCommand.current?.payload !== fingerprint) lastCommand.current = { payload: fingerprint, key: crypto.randomUUID() };
    const key = lastCommand.current.key;
    const controller = new AbortController();
    request.current = controller;
    setPending(true);
    setError(null);
    try {
      if (mode === "create") await medicalPatientsApi.create(payload as Parameters<typeof medicalPatientsApi.create>[0], key, controller.signal);
      else if (mode === "preliminary") await medicalPatientsApi.preliminary(patient!.id, payload as Parameters<typeof medicalPatientsApi.preliminary>[1], key, controller.signal);
      else if (mode === "verify") await medicalPatientsApi.verify(patient!.id, payload as Parameters<typeof medicalPatientsApi.verify>[1], key, controller.signal);
      else await medicalPatientsApi.correct(patient!.id, payload as Parameters<typeof medicalPatientsApi.correct>[1], key, controller.signal);
      if (!controller.signal.aborted) onSaved();
    } catch (cause) {
      if (controller.signal.aborted) return;
      const status = axios.isAxiosError(cause) ? cause.response?.status : undefined;
      if (status === 401 || status === 403) onDenied();
      else { setConflict(status === 409); setError(cause); }
    } finally {
      request.current = null;
      if (!controller.signal.aborted) setPending(false);
    }
  }

  return <form className="space-y-4" autoComplete="off" onSubmit={event => { event.preventDefault(); void submit(); }}>
    <p className="break-words text-sm font-semibold text-platforma-text">{patient?.full_name ?? clientName}</p>
    {mode === "verify" && patient ? <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
      {[["birth", patient.demographics.date_of_birth], ["sex", patient.demographics.sex], ["address", patient.demographics.address], ["iin", patient.iin]].map(([label, value]) =>
        <div key={label} className="min-w-0"><dt className="text-platforma-subtle">{t(`medical.${label}`)}</dt><dd className="mt-1 whitespace-pre-wrap break-words text-platforma-text">{value || "—"}</dd></div>)}
    </dl> : null}
    <fieldset disabled={pending || conflict} className="min-w-0 space-y-4">
      {mode === "correct" ? <Input label={t("medical.fullName")} value={name} onChange={event => setName(event.target.value)} required maxLength={255} className="min-h-11 text-base sm:text-sm" /> : null}
      {mode !== "verify" ? <>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Input label={t("medical.birth")} type="date" value={birth} onChange={event => setBirth(event.target.value)} className="min-h-11 text-base sm:text-sm" />
          <Input label={t("medical.sex")} value={sex} onChange={event => setSex(event.target.value)} maxLength={32} className="min-h-11 text-base sm:text-sm" />
        </div>
        <Textarea label={t("medical.address")} value={address} onChange={event => setAddress(event.target.value)} maxLength={2000} className="text-base sm:text-sm" />
        {mode !== "correct" ? <Input label={t("medical.iin")} value={iin} onChange={event => setIin(event.target.value)} inputMode="numeric" pattern="[0-9]{12}" maxLength={12} className="min-h-11 text-base sm:text-sm" /> : null}
      </> : null}
      {mode === "preliminary" || mode === "correct" ? <Textarea label={t("medical.reason")} required value={reason} onChange={event => setReason(event.target.value)} maxLength={2000} className="text-base sm:text-sm" /> : null}
      {needsProtocol ? protocolError ? <ErrorState message={getApiErrorMessage(protocolError)} action={<Button type="button" variant="secondary" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} /> : !protocol ? <LoadingState /> : <>
        <Select label={t("medical.method")} value={method} options={protocol.methods.map(item => ({ value: item.code, label: item.label[language] }))}
          onChange={event => { setMethod(event.target.value); setFields({}); }} />
        {selectedMethod?.fields.map(field => <Textarea key={field.code} label={field.label[language]} required={field.required}
          maxLength={field.max_length} value={fields[field.code] ?? ""} className="text-base sm:text-sm"
          onChange={event => setFields(current => ({ ...current, [field.code]: event.target.value }))} />)}
      </> : null}
    </fieldset>
    {error ? <ErrorState message={conflict ? t("medical.conflict") : getApiErrorMessage(error)} /> : null}
    <div className="flex flex-wrap justify-end gap-2">
      <Button type="button" variant="secondary" size="lg" disabled={pending} onClick={onCancel}>{t("common.cancel")}</Button>
      <Button type="submit" size="lg" isLoading={pending} disabled={conflict || (needsProtocol && (!protocol || !!protocolError || !selectedMethod))}>
        {t(mode === "verify" ? "medical.verify" : "common.save")}
      </Button>
    </div>
  </form>;
}
