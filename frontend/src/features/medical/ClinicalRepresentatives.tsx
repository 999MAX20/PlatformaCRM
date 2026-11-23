import { useEffect, useState } from "react";
import { medicalRepresentativesApi, type Representative } from "../../api/medicalRepresentatives";
import type { ClinicalReadScope } from "../../api/medicalClinical";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { medicalRoleDenied } from "./roles/useMedicalRolePage";
import { RepresentativeDetails } from "./RepresentativeDetails";

export function ClinicalRepresentatives({ scope }: { scope: ClinicalReadScope }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const focusId = `clinical-representatives-${scope.business_id}-${scope.patient_id}`;
  return <>
    <Button size="lg" variant="secondary" data-focus-return-id={focusId} onClick={() => setOpen(true)}>{t("medical.representatives")}</Button>
    <Modal open={open} onClose={() => setOpen(false)} title={t("medical.representatives")} size="lg"
      focusReturnId={focusId} testId="clinical-representatives">
      {open ? <RepresentativeList scope={scope} /> : null}
    </Modal>
  </>;
}

function RepresentativeList({ scope }: { scope: ClinicalReadScope }) {
  const { t } = useI18n();
  const [rows, setRows] = useState<Representative[]>([]);
  const [offset, setOffset] = useState(0);
  const [next, setNext] = useState<number | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(null); setRows([]); setNext(null);
    medicalRepresentativesApi.clinicalList(scope, offset, controller.signal).then(data => {
      if (!controller.signal.aborted) { setRows(data.results); setNext(data.next_offset); }
    }).catch(cause => { if (!controller.signal.aborted) setError(cause); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [scope, offset, attempt]);
  return <div className="min-w-0 space-y-4">
    <p className="text-sm text-platforma-subtle">{t("medical.clinical.readOnly")}</p>
    <Button size="lg" variant="secondary" disabled={loading} onClick={() => setAttempt(value => value + 1)}>{t("medical.clinical.reload")}</Button>
    {loading ? <LoadingState /> : error ? <ErrorState message={medicalRoleDenied(error) ? t("medical.denied") : getApiErrorMessage(error)}
      action={<Button size="lg" variant="secondary" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} /> : <>
      {!rows.length ? <p className="text-sm text-platforma-subtle">{t("medical.repEmpty")}</p> : <ul className="divide-y divide-platforma-border">
        {rows.map(row => <li key={row.id} className="min-w-0 space-y-2 py-3 text-sm"><RepresentativeDetails row={row} /></li>)}
      </ul>}
      <div className="flex flex-wrap gap-2">
        {offset > 0 ? <Button size="lg" variant="secondary" onClick={() => setOffset(value => Math.max(0, value - 25))}>{t("medical.repPrevious")}</Button> : null}
        {next !== null ? <Button size="lg" variant="secondary" onClick={() => setOffset(next)}>{t("medical.repNext")}</Button> : null}
      </div>
    </>}
  </div>;
}
