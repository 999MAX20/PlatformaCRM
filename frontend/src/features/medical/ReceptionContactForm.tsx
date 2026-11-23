import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { medicalReceptionApi as api, type ReceptionRequest } from "../../api/medicalReception";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { ErrorState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { ReceptionHistory } from "./ReceptionHistory";

export function ReceptionContactForm({ businessId, row, timeZone, onDirty, onPending, onDenied, onDone }: {
  businessId: number; row: ReceptionRequest; timeZone: string; onDirty: (value: boolean) => void;
  onPending: (value: boolean) => void; onDenied: (cause: unknown) => void; onDone: () => void;
}) {
  const { t } = useI18n();
  const [action, setAction] = useState(row.actions.reopen ? "reopen" : "no_answer");
  const [reason, setReason] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [conflict, setConflict] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const controller = useRef(new AbortController());
  const busy = useRef(false);
  const retry = useRef<{ fingerprint: string; key: string } | null>(null);
  useEffect(() => { heading.current?.focus(); const active = new AbortController(); controller.current = active; return () => active.abort(); }, []);
  async function submit(event: React.FormEvent) {
    event.preventDefault(); if (!reason.trim() || busy.current || conflict) return;
    const payload = { business_id: businessId, expected_revision: row.revision, action, reason: reason.trim() };
    const fingerprint = JSON.stringify(payload);
    if (retry.current?.fingerprint !== fingerprint) retry.current = { fingerprint, key: crypto.randomUUID() };
    busy.current = true; setPending(true); onPending(true); setError(null);
    try {
      await api.contact(row.id, payload, retry.current.key, controller.current.signal);
      if (!controller.current.signal.aborted) { onDirty(false); onDone(); }
    } catch (cause) {
      if (!controller.current.signal.aborted) {
        if (axios.isAxiosError(cause) && [401, 403, 404].includes(cause.response?.status ?? 0)) onDenied(cause);
        else { setError(cause); setConflict(axios.isAxiosError(cause) && cause.response?.status === 409); }
      }
    } finally { busy.current = false; onPending(false); if (!controller.current.signal.aborted) setPending(false); }
  }
  const options = row.actions.reopen ? ["reopen"] : ["no_answer", "contacted", "declined", "cancelled", ...(row.actions.expire ? ["expired"] : [])];
  return <section className="min-w-0 space-y-4" data-testid="reception-contact">
    <h2 ref={heading} tabIndex={-1} className="text-lg font-semibold">{t("medical.reception.contactTitle")}</h2>
    <p className="break-words">{row.client_name} · {row.service_name}</p>
    <p className="text-sm text-platforma-subtle">{t("medical.reception.contactPolicy")}</p>
    <form className="space-y-4" onSubmit={event => void submit(event)}>
      <fieldset disabled={pending || conflict} className="min-w-0 space-y-4">
        <Select label={t("medical.reception.contactOutcome")} value={action} options={options.map(value => ({ value, label: t(`medical.reception.contact.${value}`) }))} onChange={event => { setAction(event.target.value); onDirty(true); }} />
        <Textarea label={t("medical.reception.contactReason")} value={reason} maxLength={1000} required onChange={event => { setReason(event.target.value); onDirty(true); }} />
      </fieldset>
      {error ? <ErrorState message={conflict ? t("medical.clinical.conflict") : getApiErrorMessage(error)} /> : null}
      {conflict ? <Button type="button" size="lg" variant="secondary" onClick={() => { if (window.confirm(t("medical.clinical.discard"))) { onDirty(false); onDone(); } }}>{t("medical.clinical.reload")}</Button> :
        <Button type="submit" size="lg" isLoading={pending} disabled={!reason.trim()}>{t("medical.reception.saveOutcome")}</Button>}
    </form>
    <ReceptionHistory businessId={businessId} requestId={row.id} timeZone={timeZone} onDenied={onDenied} />
  </section>;
}
