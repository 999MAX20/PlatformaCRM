import { usePlanNavigation } from "./clinicalViewNavigation";
import { historyScopeKey } from "./clinicalHistoryNavigation";
import { useEffect, useState } from "react";
import { medicalClinicalApi, type ClinicalReadScope, type PatientVisitPlanPage } from "../../api/medicalClinical";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { formatDateTime } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import { localeByLanguage } from "../calendar/calendarConstants";
import { medicalRoleDenied } from "./roles/useMedicalRolePage";

export function ClinicalVisitPlans({ scope, entry }: { scope: ClinicalReadScope; entry: "overview" | "plan" }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const focusId = `clinical-visit-plans-${entry}-${scope.business_id}-${scope.patient_id}`;
  return <>
    <Button size="lg" variant="secondary" data-focus-return-id={focusId} onClick={() => setOpen(true)}>{t("plans.title")}</Button>
    <Modal open={open} onClose={() => setOpen(false)} title={t("plans.title")} size="lg"
      focusReturnId={focusId} testId="clinical-visit-plans">
      {open ? <PatientPlans key={historyScopeKey(scope)} scope={scope} /> : null}
    </Modal>
  </>;
}

function PatientPlans({ scope }: { scope: ClinicalReadScope }) {
  const { t, language } = useI18n();
  const [data, setData] = useState<PatientVisitPlanPage | null>(null);
  const [navigation, setNavigation] = usePlanNavigation(scope);
  const { cursor, archived } = navigation;
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    setData(null); setError(null); setLoading(true);
    medicalClinicalApi.patientPlans({ ...scope, before_id: cursor, archived }, controller.signal)
      .then(value => { if (!controller.signal.aborted) setData(value); })
      .catch(cause => { if (!controller.signal.aborted) setError(cause); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [scope, cursor, archived, attempt]);
  return <div className="min-w-0 space-y-4">
    <p className="text-sm text-platforma-subtle">{t("medical.clinical.readOnly")}</p>
    <Select label={t("plans.title")} value={archived ? "archived" : "active"} disabled={loading}
      options={[{ value: "active", label: t("plans.active") }, { value: "archived", label: t("plans.archived") }]}
      onChange={event => { setNavigation({ archived: event.target.value === "archived" }); }} />
    <Button size="lg" variant="secondary" disabled={loading} onClick={() => setAttempt(value => value + 1)}>{t("medical.clinical.reload")}</Button>
    {loading ? <LoadingState /> : error ? <ErrorState message={medicalRoleDenied(error) ? t("medical.denied") : getApiErrorMessage(error)}
      action={<Button size="lg" variant="secondary" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} /> : data ? <>
      {!data.results.length ? <p className="text-sm text-platforma-subtle">{t("plans.empty")}</p> : <ul className="space-y-4">
        {data.results.map(plan => <li key={plan.id} data-testid="clinical-visit-plan" className="min-w-0 space-y-3 rounded-card border border-platforma-border p-4">
          <h3 className="break-words font-semibold">{t("plans.plan")} #{plan.id}</h3>
          <p className="text-sm text-platforma-subtle">{formatDateTime(plan.created_at, undefined, true, localeByLanguage[language])}</p>
          {plan.terminated_at ? <p className="text-sm">{t("planClosure.terminated")}</p> : null}
          {!plan.steps.length ? <p className="text-sm">{t("plans.emptySteps")}</p> : <ol className="space-y-3">
            {plan.steps.map(step => <li key={step.id} className="space-y-1 break-words text-sm">
              <p className="font-medium">{step.service_name}</p>
              <p>{step.removed_at ? t("plans.removed") : step.appointment ? t(`status.${step.status}`) : t("plans.unscheduled")}</p>
              {step.resource_name ? <p>{step.resource_name}</p> : null}
              {step.start_at ? <p>{formatDateTime(step.start_at, undefined, true, localeByLanguage[language])}</p> : null}
            </li>)}
          </ol>}
        </li>)}
      </ul>}
      <div className="flex flex-wrap gap-2">
        {cursor !== undefined ? <Button size="lg" variant="secondary" onClick={() => setNavigation({ archived })}>{t("medical.clinical.newest")}</Button> : null}
        {data.next_before_id !== null ? <Button size="lg" variant="secondary" onClick={() => setNavigation({ archived, cursor: data.next_before_id! })}>{t("medical.clinical.older")}</Button> : null}
      </div>
    </> : null}
  </div>;
}
