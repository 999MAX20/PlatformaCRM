import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { medicalParticipationApi as api, type Participation, type ParticipationSource } from "../../api/medicalParticipation";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";

export type ParticipationFormScope = { businessId: number; patientId: number; branchId: number; source?: ParticipationSource };
export function ParticipationCommandForm({ scope, item, onSaved, onDenied, guard }: {
  scope: ParticipationFormScope; item?: Participation; onSaved: () => void; onDenied: (error: unknown) => void;
  guard: { current: { dirty: boolean; pending: boolean } };
}) {
  const { t } = useI18n();
  const [options, setOptions] = useState<Array<{ member_id: number; name: string }>>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const [revision, setRevision] = useState<number | null>(null);
  const [selected, setSelected] = useState("");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [readError, setReadError] = useState<unknown>(null);
  const [conflict, setConflict] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [after, setAfter] = useState<number | undefined>();
  const retry = useRef<{ fingerprint: string; key: string } | null>(null);
  guard.current.dirty = Boolean(selected || reason);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setReadError(null);
    const readScope = { business_id: scope.businessId, patient_id: scope.patientId, after_member_id: after };
    const read = item ? api.responsibleCandidates(item.id, readScope, controller.signal) : api.candidates({ ...readScope,
      branch_id: scope.branchId, ...scope.source }, controller.signal);
    void read.then(result => {
      if (controller.signal.aborted) return;
      const current = "participation_revision" in result ? result.participation_revision : result.patient_revision;
      setRevision(current); setCursor(result.next_after_member_id);
      setOptions(previous => after ? [...previous, ...result.results.filter(row => !previous.some(old => old.member_id === row.member_id))] : result.results);
      if (item && current !== item.revision) setConflict(true);
    }).catch(cause => {
      if (controller.signal.aborted) return;
      if (axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0)) onDenied(cause);
      else setReadError(cause);
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [scope.businessId, scope.patientId, scope.branchId, scope.source, item, after, attempt, onDenied]);
  useEffect(() => () => { guard.current = { dirty: false, pending: false }; }, [guard]);
  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (guard.current.pending || conflict || revision === null || !selected || (item && !reason.trim())) return;
    guard.current.pending = true; setPending(true); setError(null);
    const common = { business_id: scope.businessId, patient_id: scope.patientId };
    const payload = item ? { ...common, expected_revision: item.revision, responsible_member_id: Number(selected), reason }
      : { ...common, branch_id: scope.branchId, target_member_id: Number(selected), expected_patient_revision: revision, reason, ...scope.source };
    const fingerprint = JSON.stringify(payload);
    if (retry.current?.fingerprint !== fingerprint) retry.current = { fingerprint, key: crypto.randomUUID() };
    try {
      if (item && "responsible_member_id" in payload) await api.endByHead(item.id, payload, retry.current.key);
      else if ("target_member_id" in payload) await api.propose(payload, retry.current.key);
      guard.current = { dirty: false, pending: false }; onSaved();
    } catch (cause) {
      if (axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0)) onDenied(cause);
      else { setError(cause); if (axios.isAxiosError(cause) && cause.response?.status === 409) setConflict(true); }
    } finally { guard.current.pending = false; setPending(false); }
  }
  return <form onSubmit={event => void save(event)} className="space-y-4" data-testid="participation-command-form">
    {loading ? <LoadingState /> : null}
    {readError ? <ErrorState message={getApiErrorMessage(readError)} action={<Button type="button" variant="secondary" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} /> : null}
    {!loading && !readError && !options.length ? <p className="text-sm text-platforma-subtle">{t("medical.participation.noCandidates")}</p> : null}
    <Select label={t(item ? "medical.participation.responsible" : "medical.participation.doctor")} value={selected}
      disabled={pending || conflict || loading} onChange={event => setSelected(event.target.value)}
      options={[{ value: "", label: t("medical.participation.choose") }, ...options.map(row => ({ value: row.member_id, label: row.name }))]} />
    {cursor !== null ? <Button type="button" variant="secondary" disabled={loading || pending || conflict} onClick={() => setAfter(cursor)}>{t("medical.participation.more")}</Button> : null}
    <Textarea label={t("medical.participation.reason")} aria-label={t("medical.participation.reason")} value={reason} maxLength={2000}
      required={!!item} disabled={pending} readOnly={conflict} onChange={event => setReason(event.target.value)} />
    {conflict || error ? <ErrorState message={conflict ? t("medical.clinical.conflict") : getApiErrorMessage(error)} /> : null}
    <div className="flex flex-wrap gap-2">
      {conflict ? <Button type="button" size="lg" variant="secondary" onClick={() => { if (window.confirm(t("medical.clinical.discard"))) onSaved(); }}>{t("medical.clinical.reload")}</Button> : null}
      <Button type="submit" size="lg" isLoading={pending} disabled={loading || !!readError || conflict || !selected || (Boolean(item) && !reason.trim())}>{t(item ? "medical.participation.end" : "medical.participation.invite")}</Button>
    </div>
  </form>;
}
