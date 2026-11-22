import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { clinicalFields, medicalClinicalApi, type AppointmentClinicalContext, type ClinicalReadScope, type ClinicalWorkspace,
  type EncounterHistory, type EncounterVersion } from "../../api/medicalClinical";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { formatDateTime } from "../../lib/format";
import { localeByLanguage } from "../calendar/calendarConstants";

type Denied = (cause: unknown) => void;
function isDenied(cause: unknown) {
  return axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0);
}

export function ClinicalHistory({ context, onDenied }: { context: AppointmentClinicalContext; onDenied: Denied }) {
  const [cursor, setCursor] = useState<number | undefined>();
  const scope = useMemo(() => ({ business_id: context.business_id, patient_id: context.patient.id,
    appointment_id: context.appointment.id }), [context]);
  return <HistoryPage key={cursor ?? "first"} scope={scope} cursor={cursor} onPage={setCursor} onDenied={onDenied} />;
}

export function ParticipationClinicalHistory({ businessId, patientId, participationId, onDenied }: {
  businessId: number; patientId: number; participationId: number; onDenied: Denied;
}) {
  const [cursor, setCursor] = useState<number | undefined>();
  const scope = useMemo(() => ({ business_id: businessId, patient_id: patientId, participation_id: participationId }),
    [businessId, patientId, participationId]);
  return <HistoryPage key={cursor ?? "first"} scope={scope} cursor={cursor} onPage={setCursor} onDenied={onDenied} />;
}

function HistoryPage({ scope, cursor, onPage, onDenied }: {
  scope: ClinicalReadScope; cursor?: number; onPage: (cursor: number | undefined) => void; onDenied: Denied;
}) {
  const { t, language } = useI18n();
  const [data, setData] = useState<ClinicalWorkspace | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setData(null); setError(null);
    medicalClinicalApi.workspace({ ...scope, before_id: cursor }, controller.signal)
      .then(value => { if (!controller.signal.aborted) setData(value); })
      .catch(cause => { if (!controller.signal.aborted) { if (isDenied(cause)) onDenied(cause); else setError(cause); } });
    return () => controller.abort();
  }, [scope, cursor, attempt, onDenied]);
  if (error) return <ErrorState message={getApiErrorMessage(error)} action={<Button size="lg" variant="secondary" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} />;
  if (!data) return <LoadingState />;
  return <section className="space-y-4" data-testid="clinical-history">
    <h2 className="text-base font-semibold">{t("medical.clinical.history")}</h2>
    {!data.encounters.length ? <p className="text-sm text-platforma-subtle">{t("medical.clinical.historyEmpty")}</p> : <ul className="divide-y divide-platforma-border">
      {data.encounters.map(item => <li key={item.id}>
        <Button variant="ghost" size="lg" className="w-full justify-start text-left" aria-pressed={selected === item.id} onClick={() => setSelected(item.id)}>
          <span className="min-w-0 space-y-1">
            <span className="block">{formatDateTime(item.started_at, undefined, true, localeByLanguage[language])}</span>
            <span className="block break-words text-sm font-normal">{item.branch_name} · {item.primary_clinician_name || t("medical.clinical.authorUnknown")}</span>
            <span className="block text-sm font-normal">{t(`medical.clinical.state.${item.state}`)}</span>
          </span>
        </Button>
      </li>)}
    </ul>}
    <div className="flex flex-wrap gap-2">
      {cursor !== undefined ? <Button size="lg" variant="secondary" onClick={() => onPage(undefined)}>{t("medical.clinical.newest")}</Button> : null}
      {data.next_before_id !== null ? <Button size="lg" variant="secondary" onClick={() => onPage(data.next_before_id!)}>{t("medical.clinical.older")}</Button> : null}
    </div>
    {selected !== null ? <RevisionList key={selected} encounterId={selected} scope={scope} onDenied={onDenied} /> : null}
  </section>;
}

function RevisionList({ encounterId, scope, onDenied }: { encounterId: number; scope: ClinicalReadScope; onDenied: Denied }) {
  const [cursor, setCursor] = useState<number | undefined>();
  return <RevisionPage key={cursor ?? "first"} encounterId={encounterId} scope={scope} cursor={cursor} onPage={setCursor} onDenied={onDenied} />;
}

function RevisionPage({ encounterId, scope, cursor, onPage, onDenied }: {
  encounterId: number; scope: ClinicalReadScope; cursor?: number; onPage: (cursor: number | undefined) => void; onDenied: Denied;
}) {
  const { t, language } = useI18n();
  const [data, setData] = useState<EncounterHistory | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setData(null); setError(null);
    medicalClinicalApi.history(encounterId, { ...scope, before_revision: cursor }, controller.signal)
      .then(value => { if (!controller.signal.aborted) { setData(value); setSelected(value.versions[0]?.version_id ?? null); } })
      .catch(cause => { if (!controller.signal.aborted) { if (isDenied(cause)) onDenied(cause); else setError(cause); } });
    return () => controller.abort();
  }, [encounterId, scope, cursor, attempt, onDenied]);
  if (error) return <ErrorState message={getApiErrorMessage(error)} action={<Button size="lg" variant="secondary" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} />;
  if (!data) return <LoadingState />;
  return <section className="space-y-4 border-t border-platforma-border pt-4" data-testid="clinical-revisions">
    <h3 className="text-base font-semibold">{t("medical.clinical.revisions")}</h3>
    <div className="flex flex-wrap gap-2">
      {data.versions.map(item => <Button key={item.version_id} size="lg" variant={selected === item.version_id ? "secondary" : "ghost"}
        aria-pressed={selected === item.version_id} onClick={() => setSelected(item.version_id)}>
        <span>{t("medical.clinical.revision")} {item.revision}<span className="block text-xs font-normal">{formatDateTime(item.created_at, undefined, true, localeByLanguage[language])}</span></span>
      </Button>)}
    </div>
    <div className="flex flex-wrap gap-2">
      {cursor !== undefined ? <Button size="lg" variant="secondary" onClick={() => onPage(undefined)}>{t("medical.clinical.newest")}</Button> : null}
      {data.next_before_revision !== null ? <Button size="lg" variant="secondary" onClick={() => onPage(data.next_before_revision!)}>{t("medical.clinical.older")}</Button> : null}
    </div>
    {selected !== null ? <VersionReader key={selected} versionId={selected} scope={scope} onDenied={onDenied} /> : <p className="text-sm text-platforma-subtle">{t("medical.clinical.historyEmpty")}</p>}
  </section>;
}

function VersionReader({ versionId, scope, onDenied }: { versionId: number; scope: ClinicalReadScope; onDenied: Denied }) {
  const { t, language } = useI18n();
  const [data, setData] = useState<EncounterVersion | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setData(null); setError(null);
    medicalClinicalApi.version(versionId, scope, controller.signal)
      .then(value => { if (!controller.signal.aborted) setData(value); })
      .catch(cause => { if (!controller.signal.aborted) { if (isDenied(cause)) onDenied(cause); else setError(cause); } });
    return () => controller.abort();
  }, [versionId, scope, attempt, onDenied]);
  if (error) return <ErrorState message={getApiErrorMessage(error)} action={<Button size="lg" variant="secondary" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} />;
  if (!data) return <LoadingState />;
  return <article className="space-y-4 rounded-card border border-platforma-border bg-surface-card p-4" data-testid="clinical-version">
    <p className="text-sm font-semibold">{t("medical.clinical.readOnly")} · {t("medical.clinical.revision")} {data.revision}</p>
    <p className="break-words text-sm text-platforma-subtle">{data.author_name || t("medical.clinical.authorUnknown")} · {formatDateTime(data.created_at, undefined, true, localeByLanguage[language])}</p>
    <dl className="space-y-4">
      {clinicalFields.map(field => <div key={field}>
        <dt className="text-sm font-semibold text-platforma-subtle">{t(`medical.clinical.${field}`)}</dt>
        <dd className="mt-1 whitespace-pre-wrap break-words text-sm text-platforma-text">{data.content[field] || t("medical.clinical.notRecorded")}</dd>
      </div>)}
      {data.reason ? <div><dt className="text-sm font-semibold text-platforma-subtle">{t("medical.reason")}</dt><dd className="mt-1 whitespace-pre-wrap break-words text-sm">{data.reason}</dd></div> : null}
    </dl>
  </article>;
}
