import { useCallback, useEffect, useRef, useState } from "react";
import { useBlocker, useNavigate } from "react-router";
import axios from "axios";
import { medicalReceptionApi as api, type ReceptionRequest } from "../../api/medicalReception";
import { getApiErrorMessage } from "../../api/client";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import { ErrorState, ForbiddenState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { formatDateTime, dateInTimeZone } from "../../lib/format";
import { localeByLanguage } from "../calendar/calendarConstants";
import { useAuth } from "../auth/AuthProvider";
import { useReceptionAccess } from "./useReceptionAccess";
import { ReceptionBookingForm } from "./ReceptionBookingForm";
import { ReceptionExistingAppointment } from "./ReceptionExistingAppointment";
import { ReceptionHandover } from "./ReceptionHandover";
import { useUnsavedEntryWarning } from "../auth/useUnsavedEntryWarning";

export function ReceptionQueuePage() {
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const { t } = useI18n();
  const access = useReceptionAccess();
  const { setPageHeader } = usePageHeader();
  useEffect(() => { setPageHeader({ title: t("medical.reception.queue") }); return () => setPageHeader(null); }, [setPageHeader, t]);
  if (access.isLoading) return <LoadingState />;
  if (access.error) return <ErrorState error={access.error} action={<Button size="lg" onClick={() => void access.refetch()}>{t("common.retry")}</Button>} />;
  if (!business || !user || !access.allowed) return <ForbiddenState />;
  return <ReceptionQueue key={`${business.id}:${user.id}`} businessId={Number(business.id)}
    timeZone={business.timezone} branches={access.data!.branches} />;
}

function ReceptionQueue({ businessId, timeZone, branches }: {
  businessId: number; timeZone: string; branches: { id: number; name: string }[];
}) {
  const { t, language } = useI18n();
  const navigate = useNavigate();
  const [branch, setBranch] = useState(branches.length === 1 ? String(branches[0].id) : "");
  const [rows, setRows] = useState<ReceptionRequest[]>([]);
  const [next, setNext] = useState<number | null>(null);
  const [selected, setSelected] = useState<ReceptionRequest | null>(null);
  const [mode, setMode] = useState<"book" | "link" | "handover">("book");
  const returnFocus = useRef<number | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const guard = useRef({ dirty: false, pending: false });
  const controller = useRef<AbortController | null>(null);
  const retry = useRef<{ fingerprint: string; key: string } | null>(null);
  const onDirty = useCallback((value: boolean) => { guard.current.dirty = value; setDirty(value); }, []);
  const onPending = useCallback((value: boolean) => { guard.current.pending = value; setBusy(value); }, []);
  const denied = useCallback((cause: unknown) => { setRows([]); setSelected(null); setNext(null); setError(cause); onDirty(false); }, [onDirty]);
  useUnsavedEntryWarning(dirty || busy);
  const blocker = useBlocker(() => guard.current.pending || guard.current.dirty);
  useEffect(() => {
    if (blocker.state !== "blocked") return;
    if (!guard.current.pending && window.confirm(t("medical.clinical.discard"))) blocker.proceed(); else blocker.reset();
  }, [blocker, t]);
  const load = useCallback(async (offset = 0) => {
    controller.current?.abort();
    const active = new AbortController(); controller.current = active;
    if (!branch || !branches.some(item => String(item.id) === branch)) { setRows([]); setNext(null); return; }
    setLoading(true); setError(null); if (!offset) setRows([]);
    try {
      const page = await api.queue({ business_id: businessId, branch_id: Number(branch), offset }, active.signal);
      if (!active.signal.aborted) { setRows(previous => offset ? [...previous, ...page.results] : page.results); setNext(page.next_offset); }
    } catch (cause) {
      if (!active.signal.aborted) {
        if (axios.isAxiosError(cause) && [401, 403, 404].includes(cause.response?.status ?? 0)) denied(cause); else setError(cause);
      }
    } finally { if (!active.signal.aborted) setLoading(false); }
  }, [businessId, branch, branches, denied]);
  useEffect(() => { void load(); return () => controller.current?.abort(); }, [load]);
  useEffect(() => {
    if (!selected && !loading && returnFocus.current !== null) {
      document.getElementById(`reception-row-${returnFocus.current}`)?.focus(); returnFocus.current = null;
    }
  }, [selected, loading, rows]);
  async function claim(row: ReceptionRequest) {
    if (guard.current.pending) return;
    const payload = { business_id: businessId, expected_revision: row.revision };
    const fingerprint = JSON.stringify([row.id, payload]);
    if (retry.current?.fingerprint !== fingerprint) retry.current = { fingerprint, key: crypto.randomUUID() };
    onPending(true); setError(null);
    try { await api.claim(row.id, payload, retry.current.key, controller.current?.signal); await load(); }
    catch (cause) {
      if (axios.isAxiosError(cause) && [401, 403, 404].includes(cause.response?.status ?? 0)) denied(cause);
      else { setError(cause); if (axios.isAxiosError(cause) && cause.response?.status === 409) setRows([]); }
    } finally { onPending(false); }
  }
  function back() {
    if (guard.current.pending || (guard.current.dirty && !window.confirm(t("medical.clinical.discard")))) return;
    finish();
  }
  function finish() {
    returnFocus.current = selected?.id ?? null;
    setSelected(null); onDirty(false); void load();
  }
  return <section className="min-w-0 max-w-5xl space-y-4" data-testid="reception-queue">
    <h1 className="text-xl font-semibold">{t("medical.reception.queue")}</h1>
    <Select label={t("medical.branch")} value={branch} disabled={!!selected || busy} options={[
      { value: "", label: t("medical.selectBranch") }, ...branches.map(item => ({ value: item.id, label: item.name })),
    ]} onChange={event => setBranch(event.target.value)} />
    {selected ? <>
      <Button size="lg" variant="secondary" disabled={busy} onClick={back}>{t("common.back")}</Button>
      {mode === "handover" ? <ReceptionHandover key={selected.id} businessId={businessId} row={selected} timeZone={timeZone} onDirty={onDirty} onPending={onPending} onDenied={denied} onDone={finish} /> : mode === "book" ? <ReceptionBookingForm key={selected.id} businessId={businessId} row={selected} onDirty={onDirty} onPending={onPending} onDenied={denied} onDone={finish} /> :
        <ReceptionExistingAppointment key={selected.id} businessId={businessId} row={selected} timeZone={timeZone} onDirty={onDirty} onPending={onPending} onDenied={denied} onDone={finish} />}
    </> : <>
      {branch ? <Button size="lg" variant="secondary" disabled={loading || busy} onClick={() => void load()}>{t("medical.clinical.reload")}</Button> : null}
      {error ? <ErrorState message={getApiErrorMessage(error)} /> : null}
      <ul className="divide-y divide-platforma-border">{rows.map(row => <li key={row.id} id={`reception-row-${row.id}`} tabIndex={-1} className="platforma-focus-ring flex min-w-0 flex-wrap items-start justify-between gap-4 py-4" data-testid={`reception-request-${row.id}`}>
        <div className="min-w-0 space-y-1 break-words text-sm">
          <p className="text-base font-semibold">{row.client_name}</p>
          <p>{row.service_name} · {row.preferred_resource_name}</p>
          <p>{row.recommended_from} — {row.recommended_until}</p>
          <p>{t(`medical.reception.state.${row.state}`)}{row.assignee_name ? ` · ${row.assignee_name}` : ""}</p>
          {row.patient_in_clinic ? <p>{t("medical.reception.onsite")}</p> : null}
          {row.acceptance_due_at ? <p className={row.overdue ? "text-platforma-danger" : "text-platforma-subtle"}>{t("medical.reception.deadline")}: {formatDateTime(row.acceptance_due_at, timeZone, true, localeByLanguage[language])}{row.overdue ? ` · ${t("medical.reception.overdue")}` : ""}</p> : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="lg" variant="secondary" disabled={busy || loading} onClick={() => { onDirty(false); setMode("handover"); setSelected(row); }}>{t("medical.reception.handover")}</Button>
          {row.actions.claim ? <Button size="lg" disabled={busy || loading} onClick={() => void claim(row)}>{t("medical.reception.claim")}</Button> : null}
          {row.actions.book ? <Button size="lg" disabled={busy || loading} onClick={() => { onDirty(false); setMode("book"); setSelected(row); }}>{t("medical.reception.book")}</Button> : null}
          {row.actions.link ? <Button size="lg" variant="secondary" disabled={busy || loading} onClick={() => { onDirty(false); setMode("link"); setSelected(row); }}>{t("medical.reception.link")}</Button> : null}
          {row.booked_appointment_id && row.appointment_start_at ? <Button size="lg" variant="secondary" onClick={() => navigate(`/app/calendar?appointment=${row.booked_appointment_id}&date=${dateInTimeZone(row.appointment_start_at!, timeZone)}`)}>{t("medical.plan.openBooking")}</Button> : null}
        </div>
      </li>)}</ul>
      {loading ? <LoadingState /> : branch && !error && !rows.length ? <p>{t("medical.reception.empty")}</p> : null}
      {next !== null && !error ? <Button size="lg" variant="secondary" disabled={busy || loading} onClick={() => void load(next)}>{t("medical.templates.more")}</Button> : null}
    </>}
  </section>;
}
