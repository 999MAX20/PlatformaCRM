import { useEffect, useState } from "react";
import axios from "axios";
import { medicalClinicalApi, type ClinicalReadScope, type ToothPlanPage } from "../../api/medicalClinical";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { formatDateTime } from "../../lib/format";
import { localeByLanguage } from "../calendar/calendarConstants";
import { ClinicalPlanStepsRead } from "./ClinicalPlanSteps";

export function ToothPlanSteps({ scope, tooth, asOf, onDenied }: {
  scope: ClinicalReadScope; tooth: number; asOf?: string; onDenied: (cause: unknown) => void;
}) {
  const { t, language } = useI18n();
  const [page, setPage] = useState<ToothPlanPage | null>(null);
  const [cursor, setCursor] = useState<{ id: number; asOf: string }>();
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setPage(null); setError(null);
    medicalClinicalApi.toothPlan({ ...scope, tooth, as_of: cursor?.asOf ?? asOf, before_id: cursor?.id }, controller.signal)
      .then(value => { if (!controller.signal.aborted) setPage(value); })
      .catch(cause => { if (!controller.signal.aborted) {
        if (axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0)) onDenied(cause);
        else setError(cause);
      } });
    return () => controller.abort();
  }, [scope, tooth, asOf, cursor, attempt, onDenied]);
  return <section className="space-y-3 border-t border-platforma-border pt-4" data-testid="tooth-plan-steps">
    <h3 className="font-medium">{t("medical.plan.linkedToTooth")}</h3>
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button size="lg" variant="secondary"
      onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} /> : !page ? <LoadingState /> : <>
      {!page.results.length ? <p className="text-sm text-platforma-subtle">{t("medical.plan.noToothSteps")}</p> :
        page.results.map(row => <article key={row.id} className="space-y-2">
          <p className="break-words text-sm text-platforma-subtle">{row.author_name} · {t("medical.clinical.revision")} {row.revision} · {formatDateTime(row.created_at, undefined, true, localeByLanguage[language])}</p>
          <ClinicalPlanStepsRead content={{ plan_steps: [row.step] }} />
        </article>)}
      <div className="flex flex-wrap gap-2">
        {cursor ? <Button size="lg" variant="secondary" onClick={() => setCursor(undefined)}>{t("medical.clinical.newest")}</Button> : null}
        {page.next_before_id ? <Button size="lg" variant="secondary" onClick={() => setCursor({ id: page.next_before_id!, asOf: page.as_of })}>{t("medical.clinical.older")}</Button> : null}
      </div>
    </>}
  </section>;
}
