import { useEffect, useState } from "react";
import axios from "axios";
import { medicalReceptionApi as api, type ReceptionHistoryEntry } from "../../api/medicalReception";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { formatDateTime } from "../../lib/format";
import { localeByLanguage } from "../calendar/calendarConstants";

export function ReceptionHistory({ businessId, requestId, timeZone, onDenied }: {
  businessId: number; requestId: number; timeZone: string; onDenied: (cause: unknown) => void;
}) {
  const { t, language } = useI18n();
  const [rows, setRows] = useState<ReceptionHistoryEntry[]>([]);
  const [offset, setOffset] = useState(0);
  const [next, setNext] = useState<number | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(null);
    if (!offset) setRows([]);
    api.history(requestId, { business_id: businessId, offset }, controller.signal).then(page => {
      if (!controller.signal.aborted) { setRows(previous => offset ? [...previous, ...page.results] : page.results); setNext(page.next_offset); }
    }).catch(cause => {
      if (!controller.signal.aborted) {
        if (axios.isAxiosError(cause) && [401, 403, 404].includes(cause.response?.status ?? 0)) { setRows([]); onDenied(cause); }
        else setError(cause);
      }
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [businessId, requestId, offset, attempt, onDenied]);
  return <section className="space-y-3 border-t border-platforma-border pt-4" data-testid="reception-history">
    <h3 className="text-base font-semibold">{t("medical.reception.history")}</h3>
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button size="lg" variant="secondary"
      onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} /> : null}
    <ol className="divide-y divide-platforma-border">{rows.map(row => <li key={row.id} className="space-y-1 break-words py-3 text-sm">
      <p className="font-medium">{t(row.kind === "medical_follow_up_booked" ? "medical.reception.state.booked" : `medical.reception.event.${row.kind}`)}</p>
      <p>{formatDateTime(row.created_at, timeZone, true, localeByLanguage[language])}{row.actor_name ? ` · ${row.actor_name}` : ""}</p>
      {row.kind === "medical_follow_up_transferred" ? <p>{row.from_name} → {row.to_name || t("medical.reception.release")}</p> : null}
      {row.reason ? <p className="whitespace-pre-wrap">{row.reason}</p> : null}
    </li>)}</ol>
    {loading ? <LoadingState /> : !rows.length && !error ? <p>{t("medical.reception.emptyHistory")}</p> : null}
    {next !== null && !error ? <Button size="lg" variant="secondary" disabled={loading} onClick={() => setOffset(next)}>{t("medical.templates.more")}</Button> : null}
  </section>;
}
