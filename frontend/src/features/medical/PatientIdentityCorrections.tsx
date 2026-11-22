import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { medicalPatientsApi as api, type IdentityCorrection, type IdentityCorrectionsPage, type PatientScope } from "../../api/medicalPatients";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Textarea } from "../../components/ui/Textarea";
import { Modal } from "../../components/ui/Modal";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { MedicalRoleCommand, type RoleDraftState, type RoleFormControl } from "./roles/MedicalRoleCommand";

export function PatientIdentityCorrections({ scope, clientId, onDenied }: { scope: PatientScope; clientId: number; onDenied: () => void }) {
  const { t, language } = useI18n();
  const [data, setData] = useState<IdentityCorrectionsPage | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const [editing, setEditing] = useState<{ item: IdentityCorrection; approve: boolean } | null>(null);
  const [offset, setOffset] = useState(0);
  const guard = useRef<RoleDraftState>({ dirty: false, pending: false });
  const admitted = useRef(false);
  const onDraft = useCallback((state: RoleDraftState) => { guard.current = state; }, []);
  const denied = useCallback(() => { setData(null); setEditing(null); onDenied(); }, [onDenied]);
  useEffect(() => {
    const controller = new AbortController(); setError(null); setLoading(true);
    if (!offset) setData(null);
    void api.identityCorrections(scope, clientId, offset, controller.signal).then(value => {
      if (controller.signal.aborted) return;
      admitted.current = true;
      setData(previous => ({ ...value, results: offset ? [...(previous?.results ?? []), ...value.results] : value.results }));
    }).catch(cause => {
      if (controller.signal.aborted) return;
      if (axios.isAxiosError(cause) && [401, 403, 404].includes(cause.response?.status ?? 0) && admitted.current) denied();
      else setError(cause);
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [scope.business_id, scope.branch_id, clientId, attempt, offset, denied]);
  function reload() { setOffset(0); setAttempt(value => value + 1); }
  function close() {
    if (guard.current.pending || (guard.current.dirty && !window.confirm(t("medical.clinical.discard")))) return;
    guard.current = { dirty: false, pending: false }; setEditing(null);
  }
  if (!admitted.current && axios.isAxiosError(error) && [403, 404].includes(error.response?.status ?? 0)) return null;
  return <section className="space-y-4" aria-label={t("medical.correction.title")} data-testid="identity-corrections">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h3 className="text-base font-semibold">{t("medical.correction.title")}</h3>
      <Button variant="secondary" disabled={loading} onClick={reload}>{t("medical.clinical.reload")}</Button>
    </div>
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button variant="secondary" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} /> : null}
    {loading ? <LoadingState /> : null}
    {data ? <>
      {data.results.length ? <ul className="divide-y divide-platforma-border">
        {data.results.map(item => <li key={item.id} data-testid={`identity-correction-${item.id}`} className="space-y-3 py-4 text-sm">
          <p className="font-semibold">{t(`medical.correction.${item.state}`)}</p>
          <p className="break-words text-platforma-subtle">{item.requested_by} · {new Date(item.created_at).toLocaleString(language)}</p>
          <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div><dt className="text-platforma-subtle">{t("medical.correction.currentIin")}</dt><dd>{data.current_iin || "—"}</dd></div>
            <div><dt className="text-platforma-subtle">{t("medical.correction.proposedIin")}</dt><dd>{item.proposed_iin || "—"}</dd></div>
          </dl>
          <p className="whitespace-pre-wrap break-words">{t("medical.reason")}: {item.reason}</p>
          {item.decision_reason ? <p className="whitespace-pre-wrap break-words">{t("medical.correction.decisionReason")}: {item.decision_reason}</p> : null}
          {item.decided_at ? <p className="break-words text-platforma-subtle">{item.decided_by} · {new Date(item.decided_at).toLocaleString(language)}</p> : null}
          {item.state === "pending" && data.actions.approve ? <div className="flex flex-wrap gap-2">
            <Button size="lg" data-focus-return-id={`iin-review-${item.id}-true`} onClick={() => setEditing({ item, approve: true })}>{t("medical.correction.approve")}</Button>
            <Button variant="secondary" size="lg" data-focus-return-id={`iin-review-${item.id}-false`} onClick={() => setEditing({ item, approve: false })}>{t("medical.correction.reject")}</Button>
          </div> : null}
        </li>)}
      </ul> : !loading ? <p className="text-sm text-platforma-subtle">{t("medical.correction.empty")}</p> : null}
      {data.next_offset !== null ? <Button variant="secondary" disabled={loading} onClick={() => setOffset(data.next_offset!)}>{t("medical.search.more")}</Button> : null}
    </> : null}
    <Modal open={editing !== null} onClose={close} closeOnBackdrop={false} size="lg" focusReturnId={editing ? `iin-review-${editing.item.id}-${editing.approve}` : undefined}
      title={t(editing?.approve ? "medical.correction.approve" : "medical.correction.reject")}>
      {editing ? <IdentityDecision key={`${editing.item.id}:${editing.approve}`} businessId={scope.business_id} item={editing.item} approve={editing.approve}
        control={{ guard, onDraft, onDenied: denied, onSaved: () => { setEditing(null); reload(); } }} /> : null}
    </Modal>
  </section>;
}

function IdentityDecision({ businessId, item, approve, control }: { businessId: number; item: IdentityCorrection; approve: boolean; control: RoleFormControl }) {
  const { t } = useI18n();
  const [reason, setReason] = useState("");
  const payload = reason.trim() ? { business_id: businessId, approve, reason } : null;
  return <MedicalRoleCommand payload={payload} dirty={!!reason} control={control} label={t(approve ? "medical.correction.approve" : "medical.correction.reject")}
    submit={(value, key) => api.decideIdentityCorrection(item.id, value, key)}>
    <p className="break-words text-sm">{t("medical.correction.proposedIin")}: {item.proposed_iin || "—"}</p>
    <p className="whitespace-pre-wrap break-words text-sm">{t("medical.reason")}: {item.reason}</p>
    <Textarea label={t("medical.correction.decisionReason")} value={reason} onChange={event => setReason(event.target.value)} required maxLength={2000} />
  </MedicalRoleCommand>;
}
