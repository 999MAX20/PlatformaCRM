import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { medicalParticipationApi as api, type Participation, type ParticipationClosure } from "../../api/medicalParticipation";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { MedicalRoleCommand, type RoleDraftState } from "./roles/MedicalRoleCommand";
import { medicalRoleDenied } from "./roles/useMedicalRolePage";

export function ParticipationClosurePanel({ businessId, item, own, guard, onSaved, onDenied }: {
  businessId: number; item: Participation; own: boolean; guard: { current: RoleDraftState };
  onSaved: () => void; onDenied: (cause: unknown) => void;
}) {
  const { t } = useI18n();
  const [value, setValue] = useState<ParticipationClosure | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [offset, setOffset] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const [pending, setPending] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const onDraft = useCallback((state: RoleDraftState) => { guard.current = state; setPending(state.pending); }, [guard]);
  useEffect(() => { if (own) heading.current?.focus(); }, [own]);
  useEffect(() => {
    const controller = new AbortController(); setValue(null); setError(null);
    api.closure(item.id, { business_id: businessId, patient_id: item.patient_id, offset, as_head: !own }, controller.signal)
      .then(data => { if (!controller.signal.aborted) setValue(data); })
      .catch(cause => { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) onDenied(cause); else setError(cause); } });
    return () => controller.abort();
  }, [businessId, item.id, item.patient_id, own, offset, attempt, onDenied]);
  const reload = () => { setOffset(0); setAttempt(n => n + 1); };
  const counts = value?.obligations;
  return <section className="min-w-0 space-y-4" data-testid="participation-closure">
    <h3 ref={heading} tabIndex={-1} className="text-base font-semibold">{t("medical.participation.obligations")}</h3>
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button onClick={reload}>{t("common.retry")}</Button>} /> : !value ? <LoadingState /> : null}
    {value && counts ? <>
      <p className="text-sm">{t(Object.values(counts).some(row => row.count) ? "medical.participation.remaining" : "medical.participation.noRemaining")}</p>
      <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
        {(["appointments", "encounters", "documents"] as const).map(kind => <div key={kind}>
          <dt className="text-platforma-subtle">{t(`medical.participation.obligations.${kind}`)}</dt><dd className="font-semibold">{counts[kind].count}</dd>
        </div>)}
      </dl>
      <ul className="space-y-2 text-sm">
        {counts.appointments.ids.map(id => <li key={`appointment:${id}`}><Link className="platforma-focus-ring inline-flex min-h-11 items-center rounded text-brand-700 underline" to={`/app/appointments/${id}`}>{t("medical.participation.appointmentRef", { id })}</Link></li>)}
        {counts.encounters.ids.map(id => <li key={`encounter:${id}`}>{t("medical.participation.encounterRef", { id })}</li>)}
        {counts.documents.items.map(row => <li key={`document:${row.encounter_id}:${row.kind_id}:${row.version_id}`} className="break-words">
          <span className="font-medium">{row.name}</span> — {row.version_id === null ? t("medical.participation.documentAbsent") : t("medical.participation.versionRef", { id: row.version_id })}
          <Link className="platforma-focus-ring ml-2 inline-flex min-h-11 items-center rounded text-brand-700 underline" to={`/app/appointments/${row.appointment_id}`}>{t("medical.participation.appointmentRef", { id: row.appointment_id })}</Link>
        </li>)}
      </ul>
      <div className="flex flex-wrap gap-2">
        {offset > 0 ? <Button variant="secondary" disabled={pending} onClick={() => setOffset(0)}>{t("medical.clinical.newest")}</Button> : null}
        {value.next_offset !== null ? <Button variant="secondary" disabled={pending} onClick={() => setOffset(value.next_offset!)}>{t("medical.participation.more")}</Button> : null}
        <Button variant="secondary" disabled={pending} onClick={reload}>{t("medical.clinical.reload")}</Button>
      </div>
      {own && value.can_end ? <MedicalRoleCommand key={`${value.revision}:${attempt}`} dirty={false}
        payload={{ business_id: businessId, patient_id: item.patient_id, expected_revision: value.revision }}
        submit={(payload, key) => api.endOwn(item.id, payload, key)} label={t("medical.participation.endOwnConfirm")}
        control={{ guard, onDraft, onSaved, onDenied }}><p className="text-sm">{t("medical.participation.endOwnEffect")}</p></MedicalRoleCommand> : null}
    </> : null}
  </section>;
}
