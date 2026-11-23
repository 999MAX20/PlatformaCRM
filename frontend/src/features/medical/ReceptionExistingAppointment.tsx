import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { medicalReceptionApi as api, type ReceptionCandidate, type ReceptionRequest } from "../../api/medicalReception";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { formatDateTime } from "../../lib/format";
import { localeByLanguage } from "../calendar/calendarConstants";

export function ReceptionExistingAppointment({ businessId, row, timeZone, onDirty, onPending, onDenied, onDone }: {
  businessId: number; row: ReceptionRequest; timeZone: string; onDirty: (value: boolean) => void;
  onPending: (value: boolean) => void; onDenied: (cause: unknown) => void; onDone: () => void;
}) {
  const { t, language } = useI18n();
  const [rows, setRows] = useState<ReceptionCandidate[]>([]);
  const [selected, setSelected] = useState<ReceptionCandidate | null>(null);
  const [offset, setOffset] = useState(0);
  const [next, setNext] = useState<number | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [conflict, setConflict] = useState(false);
  const controller = useRef(new AbortController());
  const inFlight = useRef(false);
  const request = useRef<{ fingerprint: string; key: string } | null>(null);
  const title = useRef<HTMLHeadingElement>(null);
  useEffect(() => { title.current?.focus(); }, []);
  useEffect(() => {
    const active = new AbortController(); controller.current = active;
    setLoading(true); setError(null); if (!offset) setRows([]);
    api.candidates(row.id, { business_id: businessId, offset }, active.signal).then(page => {
      if (!active.signal.aborted) { setRows(previous => offset ? [...previous, ...page.results] : page.results); setNext(page.next_offset); }
    }).catch(cause => {
      if (!active.signal.aborted) {
        if (axios.isAxiosError(cause) && [401, 403, 404].includes(cause.response?.status ?? 0)) onDenied(cause); else setError(cause);
      }
    }).finally(() => { if (!active.signal.aborted) setLoading(false); });
    return () => active.abort();
  }, [businessId, row.id, offset, attempt, onDenied]);
  async function link() {
    if (!selected || inFlight.current || conflict) return;
    if (!window.confirm(t("medical.reception.confirmLink"))) return;
    const payload = { business_id: businessId, expected_revision: row.revision, appointment_id: selected.id,
      expected_updated_at: selected.updated_at, confirmed: true as const };
    const fingerprint = JSON.stringify(payload);
    if (request.current?.fingerprint !== fingerprint) request.current = { fingerprint, key: crypto.randomUUID() };
    inFlight.current = true; setPending(true); onPending(true); setError(null);
    try {
      await api.link(row.id, payload, request.current.key, controller.current.signal);
      if (!controller.current.signal.aborted) { onDirty(false); onDone(); }
    } catch (cause) {
      if (!controller.current.signal.aborted) {
        if (axios.isAxiosError(cause) && [401, 403, 404].includes(cause.response?.status ?? 0)) onDenied(cause);
        else { setError(cause); setConflict(axios.isAxiosError(cause) && cause.response?.status === 409); }
      }
    } finally { inFlight.current = false; onPending(false); if (!controller.current.signal.aborted) setPending(false); }
  }
  return <section className="space-y-4" data-testid="reception-existing">
    <h2 ref={title} tabIndex={-1} className="text-lg font-semibold">{t("medical.reception.link")}</h2>
    <p className="break-words">{row.client_name} · {row.service_name}</p>
    {error ? <ErrorState message={conflict ? t("medical.clinical.conflict") : getApiErrorMessage(error)} /> : null}
    {conflict ? <Button size="lg" variant="secondary" onClick={() => {
      if (window.confirm(t("medical.clinical.discard"))) { onDirty(false); onDone(); }
    }}>{t("medical.clinical.reload")}</Button> : <>
      <fieldset disabled={pending} className="space-y-2">
        <legend className="mb-2 text-sm font-semibold">{t("medical.reception.chooseAppointment")}</legend>
        {rows.map(item => <label key={item.id} className="flex min-h-11 cursor-pointer items-start gap-3 border-b border-platforma-border py-3">
          <input type="radio" name="reception-appointment" className="platforma-focus-ring mt-1 h-5 w-5 shrink-0 accent-brand-600"
            checked={selected?.id === item.id} onChange={() => { setSelected(item); onDirty(true); }} />
          <span className="min-w-0 break-words">{formatDateTime(item.start_at, timeZone, true, localeByLanguage[language])}<br />{item.resource_name}</span>
        </label>)}
      </fieldset>
      {loading ? <LoadingState /> : !rows.length && !error ? <p>{t("medical.reception.noAppointments")}</p> : null}
      <div className="flex flex-wrap gap-2">
        <Button size="lg" variant="secondary" disabled={pending || loading} onClick={() => {
          if (!selected || window.confirm(t("medical.clinical.discard"))) { setSelected(null); onDirty(false); setOffset(0); setAttempt(value => value + 1); }
        }}>{t("medical.clinical.reload")}</Button>
        {next !== null ? <Button size="lg" variant="secondary" disabled={pending || loading} onClick={() => setOffset(next)}>{t("medical.templates.more")}</Button> : null}
        <Button size="lg" disabled={!selected || loading} isLoading={pending} onClick={() => void link()}>{t("medical.reception.confirm")}</Button>
      </div>
    </>}
  </section>;
}
