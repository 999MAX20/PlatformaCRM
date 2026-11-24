import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { clinicalFields, medicalClinicalApi, type AppointmentClinicalContext, type ClinicalReadScope, type ClinicalWorkspace,
  type EncounterHistory, type EncounterVersion, type ClinicalHistoryOptions } from "../../api/medicalClinical";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { formatDateTime } from "../../lib/format";
import { localeByLanguage } from "../calendar/calendarConstants";
import { ClinicalPlanStepsRead } from "./ClinicalPlanSteps";
import { EncounterOrdersEntry } from "./orders/OrderWorkspace";
import { EncounterDocumentsEntry } from "./documents/DocumentWorkspace";

import { ClinicalHistoryFilters } from "./ClinicalHistoryFilters";
import { historyScopeKey, useHistoryNavigation, type HistoryMemory, type HistoryNavigation } from "./clinicalHistoryNavigation";

type Denied = (cause: unknown) => void;
function isDenied(cause: unknown) {
  return axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0);
}

export function ClinicalHistory({ context, onDenied, memory }: { context: AppointmentClinicalContext; onDenied: Denied; memory?: HistoryMemory }) {
  const scope = useMemo(() => ({ business_id: context.business_id, patient_id: context.patient.id,
    appointment_id: context.appointment.id }), [context]);
  return <HistoryPage key={historyScopeKey(scope)} scope={scope} memory={memory} onDenied={onDenied} />;
}

export function ParticipationClinicalHistory({ businessId, patientId, participationId, onDenied, memory }: {
  businessId: number; patientId: number; participationId: number; onDenied: Denied; memory?: HistoryMemory;
}) {
  const scope = useMemo(() => ({ business_id: businessId, patient_id: patientId, participation_id: participationId }),
    [businessId, patientId, participationId]);
  return <HistoryPage key={historyScopeKey(scope)} scope={scope} memory={memory} onDenied={onDenied} />;
}

function HistoryPage({ scope, memory, onDenied }: {
  scope: ClinicalReadScope; memory?: HistoryMemory; onDenied: Denied;
}) {
  const { t, language } = useI18n();
  const [data, setData] = useState<ClinicalWorkspace | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const [navigation, change] = useHistoryNavigation(scope, memory);
  const { cursor, selected, filters } = navigation;
  const [options, setOptions] = useState<ClinicalHistoryOptions>({ branches: [], authors: [] });
  const onPage = (value: number | undefined) => change({ ...navigation, cursor: value, selected: undefined });
  useEffect(() => {
    const controller = new AbortController();
    setData(null); setError(null);
    medicalClinicalApi.workspace({ ...scope, ...filters, before_id: cursor }, controller.signal)
      .then(value => { if (!controller.signal.aborted) { setData(value); setOptions(value.filter_options ?? { branches: [], authors: [] }); } })
      .catch(cause => { if (!controller.signal.aborted) { if (isDenied(cause)) onDenied(cause); else setError(cause); } });
    return () => controller.abort();
  }, [scope, cursor, filters, attempt, onDenied]);
  return <section className="space-y-4" data-testid="clinical-history">
    <h2 className="text-base font-semibold">{t("medical.clinical.history")}</h2>
    <ClinicalHistoryFilters value={navigation.input} options={options} loading={!data && !error}
      onChange={input => change({ ...navigation, input })}
      onApply={() => { change({ ...navigation, filters: { ...navigation.input }, cursor: undefined, selected: undefined }); }}
      onReset={() => change({ filters: {}, input: {}, revisions: {} })} />
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button size="lg" variant="secondary" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} /> : !data ? <LoadingState /> : <>
    {!data.encounters.length ? <p className="text-sm text-platforma-subtle">{t("medical.clinical.historyEmpty")}</p> : <ul className="divide-y divide-platforma-border">
      {data.encounters.map(item => <li key={item.id}>
        <Button variant="ghost" size="lg" className="w-full justify-start text-left" aria-pressed={selected === item.id} onClick={() => change({ ...navigation, selected: item.id })}>
          <span className="min-w-0 space-y-1">
            <span className="block">{formatDateTime(item.started_at, undefined, true, localeByLanguage[language])}</span>
            <span className="block break-words text-sm font-normal">{item.branch_name} · {item.primary_clinician_name || t("medical.clinical.authorUnknown")}</span>
            <span className="block break-words text-sm font-normal">{t("medical.clinical.currentAuthor")}: {item.author_name || t("medical.clinical.authorUnknown")}</span>
            <span className="block text-sm font-normal">{t(`medical.clinical.state.${item.state}`)}</span>
          </span>
        </Button>
      </li>)}
    </ul>}
    <div className="flex flex-wrap gap-2">
      {cursor !== undefined ? <Button size="lg" variant="secondary" onClick={() => onPage(undefined)}>{t("medical.clinical.newest")}</Button> : null}
      {data.next_before_id !== null ? <Button size="lg" variant="secondary" onClick={() => onPage(data.next_before_id!)}>{t("medical.clinical.older")}</Button> : null}
    </div>
    {selected !== undefined && data.encounters.some(item => item.id === selected) ? <>
      {data.encounters.filter(item => item.id === selected).map(item => <div key={item.id} className="flex flex-wrap gap-2">
        <EncounterOrdersEntry scope={scope} encounter={item} />
        <EncounterDocumentsEntry scope={scope} encounter={item} />
      </div>)}
      <RevisionPage key={`${selected}:${navigation.revisions[selected]?.cursor ?? "first"}`} encounterId={selected} scope={scope} onDenied={onDenied} navigation={navigation} onNavigate={change} />
    </> : null}
    </>}
  </section>;
}

function RevisionPage({ encounterId, scope, onDenied, navigation, onNavigate }: {
  encounterId: number; scope: ClinicalReadScope; onDenied: Denied;
  navigation: HistoryNavigation; onNavigate: (next: HistoryNavigation) => void;
}) {
  const remembered = navigation.revisions[encounterId] ?? {};
  const cursor = remembered.cursor;
  const onPage = (value: number | undefined) => onNavigate({ ...navigation,
    revisions: { ...navigation.revisions, [encounterId]: { cursor: value } } });
  const setSelected = (value: number) => onNavigate({ ...navigation,
    revisions: { ...navigation.revisions, [encounterId]: { ...remembered, selected: value } } });
  const { t, language } = useI18n();
  const [data, setData] = useState<EncounterHistory | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const selected = data?.versions.some(item => item.version_id === remembered.selected) ? remembered.selected! : data?.versions[0]?.version_id ?? null;
  useEffect(() => {
    const controller = new AbortController();
    setData(null); setError(null);
    medicalClinicalApi.history(encounterId, { ...scope, before_revision: cursor }, controller.signal)
      .then(value => { if (!controller.signal.aborted) { setData(value); } })
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
        <dd className="mt-1 whitespace-pre-wrap break-words text-sm text-platforma-text">{data.content.not_applicable?.[field] !== undefined
          ? `${t("medical.clinical.notApplicable")}: ${data.content.not_applicable[field]}`
          : data.content[field] || t("medical.clinical.notRecorded")}</dd>
      </div>)}
      {data.reason ? <div><dt className="text-sm font-semibold text-platforma-subtle">{t("medical.reason")}</dt><dd className="mt-1 whitespace-pre-wrap break-words text-sm">{data.reason}</dd></div> : null}
    </dl>
    <ClinicalPlanStepsRead content={data.content} />
    {!!data.content.procedure_items?.length && <section className="space-y-2"><h3 className="font-semibold">{t("medical.page.treatment")}</h3>
      <ul className="space-y-2">{data.content.procedure_items.map(item => <li key={item.id} className="break-words border-t border-platforma-border pt-2">
        <strong>{item.service_name}</strong> · {item.teeth.join(", ")} · {t("medical.page.minutes", { count: item.duration_minutes })}
        <p className="whitespace-pre-wrap">{item.description}</p>
      </li>)}</ul>
    </section>}
  </article>;
}
