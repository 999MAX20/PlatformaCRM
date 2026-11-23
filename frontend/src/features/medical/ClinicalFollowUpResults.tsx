import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import axios from "axios";
import { medicalReceptionApi, type FollowUpScope, type ReceptionRequest } from "../../api/medicalReception";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { formatDateTime, dateInTimeZone } from "../../lib/format";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { localeByLanguage } from "../calendar/calendarConstants";

export function ClinicalFollowUpResults({ scope, onDenied, unsaved }: {
  scope: FollowUpScope; onDenied: (cause: unknown) => void; unsaved: boolean;
}) {
  const { t, language } = useI18n();
  const navigate = useNavigate();
  const { business } = useActiveBusiness();
  const [rows, setRows] = useState<ReceptionRequest[]>([]);
  const [next, setNext] = useState<number | null>(null);
  const [offset, setOffset] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(null); if (!offset) setRows([]);
    medicalReceptionApi.primary({ ...scope, offset }, controller.signal).then(page => {
      if (!controller.signal.aborted) { setRows(previous => offset ? [...previous, ...page.results] : page.results); setNext(page.next_offset); }
    }).catch(cause => {
      if (!controller.signal.aborted) {
        if (axios.isAxiosError(cause) && [401, 403, 404].includes(cause.response?.status ?? 0)) { setRows([]); onDenied(cause); }
        else setError(cause);
      }
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [scope.business_id, scope.patient_id, scope.encounter_id, scope.participation_id, offset, attempt, onDenied]);
  const timeZone = business?.timezone || "UTC";
  return <section className="space-y-3 border-t border-platforma-border pt-4" data-testid="clinical-follow-up-results">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h2 className="text-base font-semibold">{t("medical.reception.results")}</h2>
      <Button type="button" size="lg" variant="secondary" disabled={loading} onClick={() => { setOffset(0); setAttempt(value => value + 1); }}>{t("medical.clinical.reload")}</Button>
    </div>
    {error ? <ErrorState message={getApiErrorMessage(error)} /> : null}
    <ul className="divide-y divide-platforma-border">{rows.map(row => <li key={row.id} className="space-y-2 py-3" data-testid={`clinical-follow-up-${row.id}`}>
      <p className="break-words font-medium">{row.service_name} · {row.recommended_from} — {row.recommended_until}</p>
      <p className="break-words text-sm">{t(`medical.reception.state.${row.state}`)}{row.assignee_name ? ` · ${row.assignee_name}` : ""}</p>
      {row.appointment_start_at ? <p className="text-sm">{formatDateTime(row.appointment_start_at, timeZone, true, localeByLanguage[language])}</p> : null}
      {row.booked_appointment_id && row.appointment_start_at ? <Button type="button" size="lg" variant="secondary" disabled={unsaved}
        onClick={() => navigate(`/app/calendar?appointment=${row.booked_appointment_id}&date=${dateInTimeZone(row.appointment_start_at!, timeZone)}`)}>{t("medical.plan.openBooking")}</Button> : null}
    </li>)}</ul>
    {loading ? <LoadingState /> : !error && !rows.length ? <p className="text-sm text-platforma-subtle">{t("medical.reception.noRequests")}</p> : null}
    {next !== null && !error ? <Button type="button" size="lg" variant="secondary" disabled={loading} onClick={() => setOffset(next)}>{t("medical.templates.more")}</Button> : null}
  </section>;
}
