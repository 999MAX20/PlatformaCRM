import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { medicalParticipationApi as api, type Participation } from "../../api/medicalParticipation";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Textarea } from "../../components/ui/Textarea";
import { ErrorState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";

export function ParticipationDeclineForm({ businessId, item, guard, onSaved, onCancel, onDenied }: {
  businessId: number; item: Participation; guard: { current: { dirty: boolean; pending: boolean } };
  onSaved: () => void; onCancel: () => void; onDenied: (cause: unknown) => void;
}) {
  const { t } = useI18n();
  const [reason, setReason] = useState("");
  const [pending, setPending] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const field = useRef<HTMLTextAreaElement>(null);
  const retry = useRef<{ fingerprint: string; key: string } | null>(null);
  guard.current.dirty = Boolean(reason);
  useEffect(() => {
    field.current?.focus();
    const warn = (event: BeforeUnloadEvent) => { if (guard.current.dirty || guard.current.pending) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("beforeunload", warn);
    return () => { window.removeEventListener("beforeunload", warn); guard.current = { dirty: false, pending: false }; };
  }, [guard]);
  function close(callback: () => void) {
    if (!guard.current.pending && (!guard.current.dirty || window.confirm(t("medical.clinical.discard")))) {
      guard.current.dirty = false; callback();
    }
  }
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!reason.trim() || conflict || guard.current.pending) return;
    const payload = { business_id: businessId, patient_id: item.patient_id, expected_revision: item.revision, decision: "decline" as const, reason };
    const fingerprint = JSON.stringify(payload);
    if (retry.current?.fingerprint !== fingerprint) retry.current = { fingerprint, key: crypto.randomUUID() };
    guard.current.pending = true; setPending(true); setError(null);
    try {
      await api.respond(item.id, payload, retry.current.key);
      guard.current = { dirty: false, pending: false }; onSaved();
    } catch (cause) {
      const status = axios.isAxiosError(cause) ? cause.response?.status : undefined;
      if ([401, 403, 404].includes(status ?? 0)) { setReason(""); onDenied(cause); }
      else { setError(cause); if (status === 409) setConflict(true); }
    } finally { guard.current.pending = false; setPending(false); }
  }
  return <form className="space-y-4" data-testid="participation-decline-form" onSubmit={event => void submit(event)}>
    <Textarea ref={field} label={t("medical.participation.declineReason")} value={reason} required maxLength={2000}
      disabled={pending} readOnly={conflict} onChange={event => setReason(event.target.value)} />
    {error ? <ErrorState message={conflict ? t("medical.clinical.conflict") : getApiErrorMessage(error)} /> : null}
    <div className="flex flex-wrap gap-2">
      <Button type="submit" size="lg" isLoading={pending} disabled={pending || conflict || !reason.trim()}>{t("medical.participation.decline")}</Button>
      {conflict ? <Button type="button" variant="secondary" onClick={() => close(onSaved)}>{t("medical.clinical.reload")}</Button> : null}
      <Button type="button" variant="secondary" disabled={pending} onClick={() => close(onCancel)}>{t("common.cancel")}</Button>
    </div>
  </form>;
}
