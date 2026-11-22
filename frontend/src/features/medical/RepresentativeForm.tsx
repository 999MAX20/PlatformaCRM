import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { clientsApi } from "../../api/clients";
import { getApiErrorMessage } from "../../api/client";
import { medicalRepresentativesApi, type Representative, type RepresentativeForm as Protocol } from "../../api/medicalRepresentatives";
import type { PatientAdministration, PatientScope } from "../../api/medicalPatients";
import type { Client } from "../../types";
import { ClientPicker } from "../../components/forms/ClientPicker";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";

function localNow() {
  const date = new Date();
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

export function RepresentativeForm({ patient, scope, relation, onSaved, onDenied, onCancel }: {
  patient: PatientAdministration; scope: PatientScope; relation: Representative | null;
  onSaved: () => void; onDenied: () => void; onCancel: () => void;
}) {
  const { t, language } = useI18n();
  const [protocol, setProtocol] = useState<Protocol | null>(null);
  const [protocolError, setProtocolError] = useState<unknown>(null);
  const [clientId, setClientId] = useState("");
  const [client, setClient] = useState<Client | null>(null);
  const [clientError, setClientError] = useState<unknown>(null);
  const [method, setMethod] = useState("");
  const [fields, setFields] = useState<Record<string, string>>({});
  const [permissions, setPermissions] = useState<string[]>([]);
  const [start, setStart] = useState(localNow);
  const [end, setEnd] = useState("");
  const [reason, setReason] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState<unknown>(null);
  const [pending, setPending] = useState(false);
  const [conflict, setConflict] = useState(false);
  const request = useRef<AbortController | null>(null);
  const last = useRef<{ payload: string; key: string } | null>(null);
  const selectedMethod = protocol?.methods.find(item => item.code === method);
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    if (relation) return;
    const controller = new AbortController();
    setProtocolError(null); setProtocol(null);
    medicalRepresentativesApi.form(scope, controller.signal).then(value => {
      if (!controller.signal.aborted) { setProtocol(value); setMethod(value.methods[0]?.code ?? ""); }
    }).catch(cause => {
      if (controller.signal.aborted) return;
      if (axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0)) onDenied();
      else setProtocolError(cause);
    });
    return () => controller.abort();
  }, [scope.business_id, scope.branch_id, relation, attempt]);
  useEffect(() => {
    let cancelled = false;
    setClient(null); setClientError(null);
    if (clientId) void clientsApi.get(Number(clientId)).then(value => {
      if (!cancelled) setClient(value);
    }).catch(cause => { if (!cancelled) setClientError(cause); });
    return () => { cancelled = true; };
  }, [clientId, attempt]);
  const validClient = client && client.business === scope.business_id && Number(client.id) !== patient.client_id && !client.is_archived;
  async function submit() {
    if (request.current || conflict) return;
    if (!relation && (!protocol || !validClient || !permissions.length || !start)) return;
    const payload = relation ? { ...scope, representative_client_id: relation.representative_client_id,
      expected_revision: relation.revision, reason } : {
      ...scope, representative_client_id: Number(client!.id), expected_patient_revision: patient.revision,
      expected_client_updated_at: client!.updated_at, protocol_reference: protocol!.reference, method, fields, permissions,
      valid_from: new Date(start).toISOString(), valid_until: end ? new Date(end).toISOString() : null,
    };
    const fingerprint = JSON.stringify(payload);
    if (last.current?.payload !== fingerprint) last.current = { payload: fingerprint, key: crypto.randomUUID() };
    const controller = new AbortController(); request.current = controller; setPending(true); setError(null);
    try {
      if (relation) await medicalRepresentativesApi.revoke(patient.id, relation.id, payload as Parameters<typeof medicalRepresentativesApi.revoke>[2], last.current.key, controller.signal);
      else await medicalRepresentativesApi.verify(patient.id, payload as Parameters<typeof medicalRepresentativesApi.verify>[1], last.current.key, controller.signal);
      if (!controller.signal.aborted) onSaved();
    } catch (cause) {
      if (controller.signal.aborted) return;
      const status = axios.isAxiosError(cause) ? cause.response?.status : undefined;
      if (status === 401 || status === 403) onDenied();
      else { setConflict(status === 409); setError(cause); }
    } finally { request.current = null; if (!controller.signal.aborted) setPending(false); }
  }
  return <form className="space-y-4" autoComplete="off" onSubmit={event => { event.preventDefault(); void submit(); }}>
    <p className="break-words text-sm font-semibold text-platforma-text">{patient.full_name}</p>
    <fieldset disabled={pending || conflict} className="min-w-0 space-y-4">
      {relation ? <><p className="break-words text-sm text-platforma-text">{relation.full_name}</p>
        <Textarea required label={t("medical.repReason")} value={reason} onChange={event => setReason(event.target.value)} maxLength={2000} className="text-base sm:text-sm" /></> : <>
        <ClientPicker value={clientId} onChange={setClientId} businessId={scope.business_id} label={t("medical.representative")} />
        {clientId && !client && !clientError ? <LoadingState /> : null}
        {clientError ? <ErrorState message={getApiErrorMessage(clientError)} action={<Button type="button" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} /> : null}
        {client && !validClient ? <p role="alert" className="text-sm text-platforma-text">{t("medical.repSelectOther")}</p> : null}
        {protocolError ? <ErrorState message={getApiErrorMessage(protocolError)} action={<Button type="button" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} /> : !protocol ? <LoadingState /> : <>
          <Select label={t("medical.method")} value={method} options={protocol.methods.map(item => ({ value: item.code, label: item.label[language] }))}
            onChange={event => { setMethod(event.target.value); setFields({}); }} />
          {selectedMethod?.fields.map(field => <Textarea key={field.code} label={field.label[language]} required={field.required} maxLength={field.max_length}
            value={fields[field.code] ?? ""} onChange={event => setFields(value => ({ ...value, [field.code]: event.target.value }))} className="text-base sm:text-sm" />)}
          <fieldset className="space-y-2"><legend className="mb-2 text-sm font-semibold text-platforma-subtle">{t("medical.repPermissions")}</legend>
            {protocol.permissions.map(item => <label key={item.code} className="flex min-h-11 cursor-pointer items-center gap-3 text-sm text-platforma-text">
              <input type="checkbox" className="platforma-focus-ring h-5 w-5 shrink-0 accent-brand-600" checked={permissions.includes(item.code)}
                onChange={event => setPermissions(value => event.target.checked ? [...value, item.code] : value.filter(code => code !== item.code))} />
              <span className="break-words">{item.label[language]}</span></label>)}
          </fieldset>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Input type="datetime-local" required label={t("medical.repFrom")} value={start} onChange={event => setStart(event.target.value)} />
            <Input type="datetime-local" required={protocol.requires_expiry} label={t("medical.repUntil")} value={end} onChange={event => setEnd(event.target.value)} />
          </div>
        </>}
      </>}
    </fieldset>
    {error ? <ErrorState message={conflict ? t("medical.conflict") : getApiErrorMessage(error)} /> : null}
    <div className="flex flex-wrap justify-end gap-2">
      <Button type="button" variant="secondary" size="lg" disabled={pending} onClick={onCancel}>{t("common.cancel")}</Button>
      <Button type="submit" size="lg" isLoading={pending} disabled={conflict || (!relation && (!protocol || !!protocolError || !validClient || !permissions.length))}>
        {t(relation ? "medical.repRevoke" : "medical.repVerify")}
      </Button>
    </div>
  </form>;
}
