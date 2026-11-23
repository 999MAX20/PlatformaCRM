import { useEffect, useMemo, useState, type ReactNode } from "react";
import axios from "axios";
import { medicalClinicalApi, type AppointmentClinicalContext, type ClinicalReadScope, type ClinicalOverview as OverviewData, type EncounterVersion } from "../../api/medicalClinical";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { formatDateTime } from "../../lib/format";
import { localeByLanguage } from "../calendar/calendarConstants";

export function ClinicalOverview({ context, onDenied, onNavigate }: {
  context: AppointmentClinicalContext; onDenied: (cause: unknown) => void;
  onNavigate: (tab: "encounter" | "history" | "orders" | "documents") => void;
}) {
  const { t } = useI18n();
  const scope = useMemo(() => ({ business_id: context.business_id, patient_id: context.patient.id,
    appointment_id: context.appointment.id }), [context]);
  return <ClinicalOverviewRead scope={scope} onDenied={onDenied} onHistory={() => onNavigate("history")} actions={<>
    <Button size="lg" onClick={() => onNavigate("encounter")}>{t("medical.clinical.note")}</Button>
    {context.encounter ? <>
      <Button size="lg" variant="secondary" onClick={() => onNavigate("orders")}>{t("medical.orders.title")}</Button>
      <Button size="lg" variant="secondary" onClick={() => onNavigate("documents")}>{t("medical.documents.title")}</Button>
    </> : null}
  </>} />;
}

export function ParticipationClinicalOverview({ businessId, patientId, participationId, onDenied, onHistory }: {
  businessId: number; patientId: number; participationId: number;
  onDenied: (cause: unknown) => void; onHistory: () => void;
}) {
  const scope = useMemo(() => ({ business_id: businessId, patient_id: patientId, participation_id: participationId }),
    [businessId, patientId, participationId]);
  return <ClinicalOverviewRead scope={scope} onDenied={onDenied} onHistory={onHistory} />;
}

function ClinicalOverviewRead({ scope, onDenied, onHistory, actions }: {
  scope: ClinicalReadScope; onDenied: (cause: unknown) => void; onHistory: () => void; actions?: ReactNode;
}) {
  const { t, language } = useI18n();
  const [data, setData] = useState<OverviewData | null>(null);
  const [source, setSource] = useState<EncounterVersion | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setData(null); setSource(null); setError(null);
    async function load() {
      try {
        const overview = await medicalClinicalApi.overview(scope, controller.signal);
        const version = overview.latest_encounter
          ? await medicalClinicalApi.version(overview.latest_encounter.version_id, scope, controller.signal) : null;
        if (!controller.signal.aborted) { setData(overview); setSource(version); }
      } catch (cause) {
        if (!controller.signal.aborted) {
          if (axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0)) onDenied(cause);
          else setError(cause);
        }
      }
    }
    void load();
    return () => controller.abort();
  }, [scope, attempt, onDenied]);
  if (error) return <ErrorState message={getApiErrorMessage(error)} action={<Button size="lg" variant="secondary" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} />;
  if (!data) return <LoadingState />;
  const latest = data.latest_encounter;
  return <section className="min-w-0 space-y-5" data-testid="clinical-overview">
    <h2 className="text-base font-semibold">{t("medical.overview.title")}</h2>
    <dl className="grid min-w-0 gap-4 sm:grid-cols-2">
      <div><dt className="text-sm text-platforma-subtle">{t("medical.birth")}</dt>
        <dd className="mt-1 break-words text-sm">{data.date_of_birth || t("medical.clinical.notRecorded")}</dd></div>
      <div><dt className="text-sm text-platforma-subtle">{t("medical.overview.latest")}</dt>
        <dd className="mt-1 break-words text-sm">{latest ? formatDateTime(latest.started_at, undefined, true, localeByLanguage[language]) : t("medical.clinical.historyEmpty")}</dd></div>
      {latest ? <>
        <div><dt className="text-sm text-platforma-subtle">{t("medical.branch")}</dt><dd className="mt-1 break-words text-sm">{latest.branch_name}</dd></div>
        <div><dt className="text-sm text-platforma-subtle">{t("medical.overview.clinician")}</dt><dd className="mt-1 break-words text-sm">{latest.primary_clinician_name || t("medical.clinical.authorUnknown")}</dd></div>
      </> : null}
    </dl>
    <div className="space-y-3 rounded-card border border-platforma-border bg-surface-card p-4" data-testid="clinical-overview-risks">
      <h3 className="text-sm font-semibold">{t("medical.overview.savedRisks")}</h3>
      <dl className="space-y-3">
        {(["allergies", "contraindications"] as const).map(field => <div key={field}>
          <dt className="text-sm font-semibold text-platforma-subtle">{t(`medical.clinical.${field}`)}</dt>
          <dd className="mt-1 whitespace-pre-wrap break-words text-sm">{source?.content.not_applicable?.[field] !== undefined
            ? `${t("medical.clinical.notApplicable")}: ${source.content.not_applicable[field]}`
            : source?.content[field] || t("medical.clinical.notRecorded")}</dd>
        </div>)}
      </dl>
      {source ? <details className="text-sm">
        <summary className="platforma-focus-ring min-h-11 cursor-pointer content-center">{t("medical.overview.source")}</summary>
        <p className="break-words">{t("medical.clinical.revision")} {source.revision} · {t(`medical.clinical.state.${latest!.state}`)}</p>
        <p className="break-words text-platforma-subtle">{source.author_name || t("medical.clinical.authorUnknown")} · {formatDateTime(source.created_at, undefined, true, localeByLanguage[language])}</p>
      </details> : null}
      <Button size="lg" variant="secondary" onClick={onHistory}>{t("medical.clinical.history")}</Button>
    </div>
    {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
  </section>;
}
