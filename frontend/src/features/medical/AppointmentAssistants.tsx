import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import axios from "axios";
import { medicalAssistantsApi as api, type AssistantAssignment, type AssistantManagementScope } from "../../api/medicalAssistants";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { medicalRoleDenied } from "./roles/useMedicalRolePage";

export function AppointmentAssistants({ scope, onPending }: {
  scope: AssistantManagementScope; onPending: (pending: boolean) => void;
}) {
  const { t } = useI18n();
  const regionId = useId();
  const { business_id, patient_id, appointment_id } = scope;
  const stableScope = useMemo(() => ({ business_id, patient_id, appointment_id }), [business_id, patient_id, appointment_id]);
  const [open, setOpen] = useState(false);
  const [admitted, setAdmitted] = useState(false);
  const [rows, setRows] = useState<AssistantAssignment[]>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [refresh, setRefresh] = useState(0);
  const [choosing, setChoosing] = useState(false);
  const [pending, setPending] = useState(false);
  const busy = useRef(false);
  const request = useRef<AbortController | null>(null);
  const retry = useRef<{ fingerprint: string; key: string } | null>(null);
  const [conflict, setConflict] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const denied = useCallback((cause: unknown) => {
    setRows([]); setCursor(null); setAdmitted(false); setChoosing(false); setError(cause); setNotice(null);
  }, []);
  const load = useCallback(async (before?: number) => {
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    setLoading(true); setError(null);
    try {
      const page = await api.managed({ ...stableScope, before_id: before }, controller.signal);
      if (!controller.signal.aborted) {
        setRows(previous => before ? [...previous, ...page.results] : page.results);
        setCursor(page.next_before_id); setAdmitted(true); setConflict(false);
      }
    } catch (cause) { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) denied(cause); else setError(cause); } }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }, [stableScope, denied]);
  useEffect(() => { void load(); return () => request.current?.abort(); }, [load, refresh]);
  useEffect(() => { onPending(pending); return () => onPending(false); }, [pending, onPending]);
  async function revoke(row: AssistantAssignment) {
    if (busy.current || conflict || !window.confirm(t("medical.assistants.confirmRevoke", { name: row.name }))) return;
    const payload = { business_id, expected_revision: row.revision };
    const fingerprint = JSON.stringify([row.id, payload]);
    if (retry.current?.fingerprint !== fingerprint) retry.current = { fingerprint, key: crypto.randomUUID() };
    busy.current = true; setPending(true); setError(null); setNotice(null);
    try {
      await api.revoke(row.id, payload, retry.current.key);
      setNotice(t("medical.assistants.revoked")); await load();
    } catch (cause) {
      if (medicalRoleDenied(cause)) denied(cause);
      else { setError(cause); setConflict(axios.isAxiosError(cause) && cause.response?.status === 409); }
    } finally { busy.current = false; setPending(false); }
  }
  if (!admitted && medicalRoleDenied(error)) return open ? <ErrorState message={t("medical.denied")} /> : null;
  if (!admitted) return error ? <ErrorState message={getApiErrorMessage(error)} action={<Button onClick={() => setRefresh(value => value + 1)}>{t("common.retry")}</Button>} /> : null;
  return <section className="min-w-0" data-testid="appointment-assistants">
    <Button size="lg" variant="secondary" aria-expanded={open} aria-controls={regionId} disabled={pending}
      onClick={() => { setOpen(value => !value); if (!open) void load(); }}>{t("medical.assistants.title")}</Button>
    <div id={regionId} hidden={!open} className="mt-3 min-w-0 space-y-3 border-b border-platforma-border pb-4">
      {open ? <>
        {notice ? <p role="status" className="text-sm">{notice}</p> : null}
        {error ? <ErrorState message={conflict ? t("medical.clinical.conflict") : getApiErrorMessage(error)}
          action={<Button disabled={pending} onClick={() => void load()}>{t("common.retry")}</Button>} /> : null}
        {choosing ? <AssistantPicker scope={stableScope} onPending={setPending} onDenied={denied} onClose={() => setChoosing(false)}
          onSaved={() => { setChoosing(false); setNotice(t("medical.assistants.invited")); void load(); }} /> : <>
          <Button size="lg" disabled={pending || loading || conflict} onClick={() => { setNotice(null); setChoosing(true); }}>{t("medical.assistants.invite")}</Button>
          <ul className="divide-y divide-platforma-border">{rows.map(row => <li key={row.id} className="flex min-w-0 flex-wrap items-center justify-between gap-3 py-3">
            <div className="min-w-0 break-words"><p className="font-medium">{row.name}</p><p className="text-sm text-platforma-subtle">{t(`medical.assistants.state.${row.state}`)}</p></div>
            {row.state === "pending" || row.state === "active" ? <Button size="lg" variant="secondary" disabled={pending || loading || conflict}
              aria-label={t("medical.assistants.revokeNamed", { name: row.name })} onClick={() => void revoke(row)}>{t("medical.assistants.revoke")}</Button> : null}
          </li>)}</ul>
          {loading ? <LoadingState /> : !error && !rows.length ? <p className="text-sm text-platforma-subtle">{t("medical.assistants.empty")}</p> : null}
          {cursor && !error ? <Button size="lg" variant="secondary" disabled={loading || pending} onClick={() => void load(cursor)}>{t("medical.templates.more")}</Button> : null}
        </>}
      </> : null}
    </div>
  </section>;
}

function AssistantPicker({ scope, onPending, onDenied, onClose, onSaved }: {
  scope: AssistantManagementScope; onPending: (pending: boolean) => void; onDenied: (cause: unknown) => void;
  onClose: () => void; onSaved: () => void;
}) {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [before, setBefore] = useState<number | undefined>();
  const [refresh, setRefresh] = useState(0);
  const [rows, setRows] = useState<{ member_id: number; name: string }[]>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const [stamp, setStamp] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [conflict, setConflict] = useState(false);
  const busy = useRef(false);
  const retry = useRef<{ fingerprint: string; key: string } | null>(null);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(null); setConflict(false);
    api.candidates({ ...scope, query: search, before_id: before }, controller.signal).then(page => {
      if (!controller.signal.aborted) { setRows(previous => before ? [...previous, ...page.results] : page.results); setCursor(page.next_before_id); setStamp(page.appointment_updated_at); }
    }).catch(cause => { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) onDenied(cause); else setError(cause); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [scope, search, before, refresh, onDenied]);
  async function invite(memberId: number) {
    if (busy.current || !stamp || conflict) return;
    const payload = { business_id: scope.business_id, patient_id: scope.patient_id, appointment_id: scope.appointment_id,
      target_member_id: memberId, expected_updated_at: stamp };
    const fingerprint = JSON.stringify(payload);
    if (retry.current?.fingerprint !== fingerprint) retry.current = { fingerprint, key: crypto.randomUUID() };
    busy.current = true; setPending(true); onPending(true); setError(null);
    try { await api.invite(payload, retry.current.key); onSaved(); }
    catch (cause) { if (medicalRoleDenied(cause)) onDenied(cause); else { setError(cause); setConflict(axios.isAxiosError(cause) && cause.response?.status === 409); } }
    finally { busy.current = false; setPending(false); onPending(false); }
  }
  return <div className="min-w-0 space-y-3">
    <Button size="lg" variant="secondary" disabled={pending} onClick={onClose}>{t("common.cancel")}</Button>
    <form className="flex flex-wrap items-end gap-3" onSubmit={event => { event.preventDefault(); setBefore(undefined); setRows([]); setSearch(query); setRefresh(value => value + 1); }}>
      <Input label={t("medical.assistants.search")} value={query} maxLength={100} disabled={pending} onChange={event => setQuery(event.target.value)} />
      <Button size="lg" type="submit" variant="secondary" disabled={pending || loading}>{t("medical.assistants.find")}</Button>
    </form>
    {error ? <ErrorState message={conflict ? t("medical.clinical.conflict") : getApiErrorMessage(error)} action={<Button disabled={pending} onClick={() => { setBefore(undefined); setRefresh(value => value + 1); }}>{t("common.retry")}</Button>} /> : null}
    <ul className="divide-y divide-platforma-border">{rows.map(row => <li key={row.member_id} className="py-2">
      <Button size="lg" variant="secondary" className="h-auto whitespace-normal text-left" disabled={loading || pending || conflict}
        onClick={() => void invite(row.member_id)}>{t("medical.assistants.inviteNamed", { name: row.name })}</Button>
    </li>)}</ul>
    {loading ? <LoadingState /> : !error && !rows.length ? <p className="text-sm text-platforma-subtle">{t("medical.assistants.noCandidates")}</p> : null}
    {cursor && !error ? <Button size="lg" variant="secondary" disabled={loading || pending} onClick={() => setBefore(cursor)}>{t("medical.templates.more")}</Button> : null}
  </div>;
}
