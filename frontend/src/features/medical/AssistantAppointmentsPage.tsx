import { useCallback, useEffect, useRef, useState } from "react";
import { useBlocker } from "react-router";
import axios from "axios";
import { medicalAssistantsApi as api, type AssistantInvitation } from "../../api/medicalAssistants";
import { getApiErrorMessage } from "../../api/client";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { Button } from "../../components/ui/Button";
import { ErrorState, ForbiddenState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { formatDateTime } from "../../lib/format";
import { localeByLanguage } from "../calendar/calendarConstants";
import { useAuth } from "../auth/AuthProvider";
import { useUnsavedEntryWarning } from "../auth/useUnsavedEntryWarning";
import { medicalRoleDenied } from "./roles/useMedicalRolePage";
import type { RoleDraftState } from "./roles/MedicalRoleCommand";
import { AssistantDraftWorkspace } from "./AssistantDraftWorkspace";

export function AssistantAppointmentsPage() {
  const { business, isLoading, error } = useActiveBusiness();
  const { user } = useAuth();
  const { t } = useI18n();
  const { setPageHeader } = usePageHeader();
  useEffect(() => { setPageHeader({ title: t("medical.assistants.mine") }); return () => setPageHeader(null); }, [setPageHeader, t]);
  if (!business || !user) return isLoading ? <LoadingState /> : error ? <ErrorState error={error} /> : <ForbiddenState />;
  return <AssistantInbox key={`${business.id}:${user.id}`} businessId={Number(business.id)} />;
}

function AssistantInbox({ businessId }: { businessId: number }) {
  const { t, language } = useI18n();
  const [rows, setRows] = useState<AssistantInvitation[]>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [conflict, setConflict] = useState(false);
  const [draft, setDraft] = useState<RoleDraftState>({ dirty: false, pending: false });
  const guard = useRef<RoleDraftState>({ dirty: false, pending: false });
  const request = useRef<AbortController | null>(null);
  const retry = useRef<{ fingerprint: string; key: string } | null>(null);
  const returnFocus = useRef<number | null>(null);
  useUnsavedEntryWarning(draft.dirty || draft.pending);
  const blocker = useBlocker(() => guard.current.dirty || guard.current.pending);
  useEffect(() => {
    if (blocker.state !== "blocked") return;
    if (!guard.current.pending && window.confirm(t("medical.clinical.discard"))) blocker.proceed();
    else blocker.reset();
  }, [blocker, t]);
  const onDraft = useCallback((value: RoleDraftState) => { guard.current = value; setDraft(value); }, []);
  const denied = useCallback((cause: unknown) => { setRows([]); setCursor(null); setSelected(null); setError(cause); onDraft({ dirty: false, pending: false }); }, [onDraft]);
  const load = useCallback(async (before?: number) => {
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    setLoading(true); setError(null); setConflict(false);
    try {
      const page = await api.mine({ business_id: businessId, before_id: before }, controller.signal);
      if (!controller.signal.aborted) { setRows(previous => before ? [...previous, ...page.results] : page.results); setCursor(page.next_before_id); }
    } catch (cause) { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) denied(cause); else setError(cause); } }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }, [businessId, denied]);
  useEffect(() => { void load(); return () => request.current?.abort(); }, [load]);
  useEffect(() => {
    if (selected === null && !loading && returnFocus.current !== null) {
      document.getElementById(`assistant-invitation-${returnFocus.current}`)?.focus();
      returnFocus.current = null;
    }
  }, [selected, loading]);
  async function accept(row: AssistantInvitation) {
    if (guard.current.pending || conflict) return;
    const payload = { business_id: businessId, expected_revision: row.revision };
    const fingerprint = JSON.stringify([row.id, payload]);
    if (retry.current?.fingerprint !== fingerprint) retry.current = { fingerprint, key: crypto.randomUUID() };
    onDraft({ dirty: false, pending: true }); setError(null);
    try { await api.accept(row.id, payload, retry.current.key); await load(); }
    catch (cause) { if (medicalRoleDenied(cause)) denied(cause); else { setError(cause); setConflict(axios.isAxiosError(cause) && cause.response?.status === 409); } }
    finally { onDraft({ dirty: false, pending: false }); }
  }
  function back() {
    if (guard.current.pending || (guard.current.dirty && !window.confirm(t("medical.clinical.discard")))) return;
    returnFocus.current = selected;
    setSelected(null); onDraft({ dirty: false, pending: false });
    void load();
  }
  return <section className="min-w-0 max-w-5xl space-y-4" data-testid="assistant-inbox">
    <h1 className="text-xl font-semibold">{t("medical.assistants.mine")}</h1>
    {selected ? <>
      <Button size="lg" variant="secondary" disabled={draft.pending} onClick={back}>{t("medical.assistants.back")}</Button>
      <AssistantDraftWorkspace key={selected} businessId={businessId} invitationId={selected} guard={guard} onDraft={onDraft} onDenied={denied} />
    </> : <>
      <Button size="lg" variant="secondary" disabled={loading || draft.pending} onClick={() => void load()}>{t("medical.clinical.reload")}</Button>
      {error ? <ErrorState message={medicalRoleDenied(error) ? t("medical.denied") : conflict ? t("medical.clinical.conflict") : getApiErrorMessage(error)}
        action={<Button disabled={draft.pending} onClick={() => void load()}>{t("common.retry")}</Button>} /> : null}
      <ul className="divide-y divide-platforma-border">{rows.map(row => <li key={row.id} className="flex min-w-0 flex-wrap items-center justify-between gap-4 py-4">
        <div className="min-w-0 break-words"><p className="font-medium">{row.clinician_name}</p>
          <p className="text-sm">{formatDateTime(row.start_at, undefined, true, localeByLanguage[language])} · {row.branch_name}</p>
          <p className="text-sm text-platforma-subtle">{t(`medical.assistants.state.${row.state}`)}</p></div>
        {row.can_accept ? <Button size="lg" disabled={loading || draft.pending || conflict} onClick={() => void accept(row)}>{t("medical.assistants.accept")}</Button> : null}
        {row.can_open ? <Button id={`assistant-invitation-${row.id}`} size="lg" variant="secondary" disabled={loading || draft.pending} onClick={() => setSelected(row.id)}>{t("medical.assistants.open")}</Button> : null}
      </li>)}</ul>
      {loading ? <LoadingState /> : !error && !rows.length ? <p className="text-sm text-platforma-subtle">{t("medical.assistants.inboxEmpty")}</p> : null}
      {cursor && !error ? <Button size="lg" variant="secondary" disabled={loading || draft.pending} onClick={() => void load(cursor)}>{t("medical.templates.more")}</Button> : null}
    </>}
  </section>;
}
