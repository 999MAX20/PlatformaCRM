import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { correctionAccessApi as api, type CorrectionAccess, type CorrectionPage, type CorrectionScope } from "../../api/medicalCorrectionAccess";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { CorrectionDecisionForm, CorrectionDraftForm, CorrectionRequestForm, type CorrectionAction } from "./CorrectionAccessForms";
import type { RoleDraftState } from "./roles/MedicalRoleCommand";

type Editing = { kind: "request" } | { kind: "edit"; item: CorrectionAccess } | { kind: "decision"; item: CorrectionAccess; action: CorrectionAction };

export function CorrectionAccessPanel({ scope }: { scope: CorrectionScope }) {
  const { t, language } = useI18n();
  const [page, setPage] = useState<CorrectionPage | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [head, setHead] = useState(false);
  const [canReview, setCanReview] = useState(false);
  const [before, setBefore] = useState<number | undefined>();
  const [attempt, setAttempt] = useState(0);
  const [editing, setEditing] = useState<Editing | null>(null);
  const admitted = useRef(false);
  const guard = useRef<RoleDraftState>({ dirty: false, pending: false });
  const onDraft = useCallback((state: RoleDraftState) => { guard.current = state; }, []);
  const onDenied = useCallback((cause: unknown) => { setPage(null); setEditing(null); setError(cause); setCanReview(false); }, []);
  const reload = useCallback(() => { setBefore(undefined); setAttempt(value => value + 1); }, []);
  const saved = useCallback(() => { setEditing(null); reload(); }, [reload]);
  useEffect(() => {
    const controller = new AbortController();
    setPage(null); setError(null); setLoading(true);
    void api.list({ ...scope, head, before_id: before }, controller.signal).then(value => {
      if (!controller.signal.aborted) { admitted.current = true; setPage(value); setCanReview(value.can_review); }
    }).catch(cause => { if (!controller.signal.aborted) { setPage(null); setEditing(null); setCanReview(false); setError(cause); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [scope.business_id, scope.branch_id, scope.client_id, head, before, attempt]);
  useEffect(() => {
    const expiry = page?.results.filter(item => item.state === "active" && item.expires_at)
      .map(item => Date.parse(item.expires_at!)).filter(Number.isFinite).sort((a, b) => a - b)[0];
    if (expiry === undefined) return;
    const timer = window.setTimeout(() => { setEditing(null); setPage(null); reload(); }, Math.max(0, expiry - Date.parse(page!.server_time)));
    return () => window.clearTimeout(timer);
  }, [page, reload]);
  function close() {
    if (guard.current.pending || (guard.current.dirty && !window.confirm(t("medical.clinical.discard")))) return;
    guard.current = { dirty: false, pending: false }; setEditing(null);
  }
  if (!admitted.current && axios.isAxiosError(error) && [403, 404].includes(error.response?.status ?? 0)) return null;
  const control = { guard, onDraft, onSaved: saved, onDenied };
  return <section className="space-y-4" aria-label={t("medical.correctionAccess.title")} data-testid="correction-access">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h3 className="text-base font-semibold">{t("medical.correctionAccess.title")}</h3>
      <Button variant="secondary" aria-disabled={loading} onClick={() => { if (!loading) reload(); }}>{t("medical.clinical.reload")}</Button>
    </div>
    {canReview ? <Select label={t("medical.correctionAccess.scope")} value={head ? "review" : "own"} onChange={event => {
      setHead(event.target.value === "review"); setBefore(undefined); setEditing(null);
    }} options={[{ value: "own", label: t("medical.correctionAccess.own") }, { value: "review", label: t("medical.correctionAccess.reviewQueue") }]} /> : null}
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button variant="secondary" onClick={reload}>{t("common.retry")}</Button>} /> : null}
    {loading ? <LoadingState /> : null}
    {page ? <>
      {!head ? <Button variant="secondary" size="lg" data-focus-return-id="correction-request" onClick={() => setEditing({ kind: "request" })}>{t("medical.correctionAccess.request")}</Button> : null}
      {!page.results.length ? <p className="text-sm text-platforma-subtle">{t("medical.correctionAccess.empty")}</p> : <ul className="divide-y divide-platforma-border">
        {page.results.map(item => <li key={item.id} className="space-y-3 py-4 text-sm" data-testid={`correction-access-${item.id}`}>
          <p className="font-semibold">{t(`medical.correctionAccess.${item.state}`)} · {t(`medical.correctionAccess.${item.document_id ? "document" : "encounter"}`)}</p>
          <p className="text-platforma-subtle">{new Date(item.created_at).toLocaleString(language)}</p>
          <p>{t("medical.correctionAccess.encounter")}: {new Date(item.encounter_started_at).toLocaleString(language)}</p>
          <p className="break-words">{t("medical.correctionAccess.requestedBy")}: {item.requester_name}</p>
          <p className="whitespace-pre-wrap break-words">{item.reason}</p>
          {item.reviewed_by_name ? <p className="break-words">{t("medical.correctionAccess.reviewedBy")}: {item.reviewed_by_name} · {item.reviewed_at ? new Date(item.reviewed_at).toLocaleString(language) : ""}</p> : null}
          {item.decision_reason ? <p className="whitespace-pre-wrap break-words">{item.decision_reason}</p> : null}
          {item.closure_reason ? <p className="whitespace-pre-wrap break-words">{item.closure_reason}</p> : null}
          {item.closed_by_name ? <p className="break-words">{t("medical.correctionAccess.closedBy")}: {item.closed_by_name} · {item.closed_at ? new Date(item.closed_at).toLocaleString(language) : ""}</p> : null}
          {item.expires_at ? <p>{t("medical.correctionAccess.until")} {new Date(item.expires_at).toLocaleString(language)}</p> : null}
          <div className="flex flex-wrap gap-2">
            {item.state === "active" && item.requester_id === page.member_id ? <Button size="lg" data-focus-return-id={`correction-edit-${item.id}`} onClick={() => setEditing({ kind: "edit", item })}>{t("medical.correctionAccess.edit")}</Button> : null}
            {(item.state === "pending" ? (head && item.requester_id !== page.member_id ? ["approve", "reject"] : item.requester_id === page.member_id ? ["withdraw"] : [])
              : item.state === "active" ? (head ? ["revoke"] : item.requester_id === page.member_id ? ["complete"] : []) : []).map(value => {
              const action = value as CorrectionAction;
              return <Button key={action} variant="secondary" size="lg" data-focus-return-id={`correction-${action}-${item.id}`}
                onClick={() => setEditing({ kind: "decision", item, action })}>{t(`medical.correctionAccess.${action}`)}</Button>;
            })}
          </div>
        </li>)}
      </ul>}
      <div className="flex flex-wrap gap-2">
        {before ? <Button variant="secondary" onClick={() => setBefore(undefined)}>{t("medical.correctionAccess.firstPage")}</Button> : null}
        {page.next_before_id ? <Button variant="secondary" onClick={() => setBefore(page.next_before_id!)}>{t("medical.correctionAccess.nextPage")}</Button> : null}
      </div>
    </> : null}
    <Modal open={editing !== null} onClose={close} closeOnBackdrop={false} title={t("medical.correctionAccess.title")} size="lg"
      focusReturnId={editing?.kind === "request" ? "correction-request" : editing?.kind === "edit" ? `correction-edit-${editing.item.id}`
        : editing?.kind === "decision" ? `correction-${editing.action}-${editing.item.id}` : undefined}>
      {editing?.kind === "request" ? <CorrectionRequestForm scope={scope} control={control} />
        : editing?.kind === "edit" ? <CorrectionDraftForm item={editing.item} businessId={scope.business_id} control={control} />
          : editing?.kind === "decision" ? <CorrectionDecisionForm item={editing.item} action={editing.action} businessId={scope.business_id} control={control} /> : null}
    </Modal>
  </section>;
}
