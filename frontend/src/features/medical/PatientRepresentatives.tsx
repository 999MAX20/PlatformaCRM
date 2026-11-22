import { useEffect, useState } from "react";
import axios from "axios";
import { getApiErrorMessage } from "../../api/client";
import { medicalRepresentativesApi, type Representative } from "../../api/medicalRepresentatives";
import type { PatientAdministration, PatientScope } from "../../api/medicalPatients";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { RepresentativeForm } from "./RepresentativeForm";

export function PatientRepresentatives({ patient, scope, canApprove, onDenied }: {
  patient: PatientAdministration; scope: PatientScope; canApprove: boolean; onDenied: () => void;
}) {
  const { t, language } = useI18n();
  const [rows, setRows] = useState<Representative[]>([]);
  const [next, setNext] = useState<number | null>(null);
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [edit, setEdit] = useState<Representative | "new" | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(null); setRows([]); setNext(null);
    medicalRepresentativesApi.list(patient.id, scope, offset, controller.signal).then(data => {
      if (!controller.signal.aborted) { setRows(data.results); setNext(data.next_offset); }
    }).catch(cause => {
      if (controller.signal.aborted) return;
      if (axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0)) onDenied();
      else setError(cause);
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [patient.id, scope.business_id, scope.branch_id, offset, refresh]);
  const date = (value: string) => new Intl.DateTimeFormat(language, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
  function close() { setEdit(null); setRefresh(value => value + 1); }
  return <section className="space-y-3 border-t border-platforma-border pt-4" aria-label={t("medical.representatives")} data-testid="patient-representatives">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h3 className="text-sm font-semibold text-platforma-text">{t("medical.representatives")}</h3>
      {canApprove ? <Button size="lg" variant="secondary" onClick={() => setEdit("new")}>{t("medical.repAdd")}</Button> : null}
    </div>
    {loading ? <LoadingState /> : error ? <ErrorState message={getApiErrorMessage(error)} action={<Button variant="secondary" onClick={() => setRefresh(value => value + 1)}>{t("common.retry")}</Button>} /> : <>
      {!rows.length ? <p className="text-sm text-platforma-subtle">{t("medical.repEmpty")}</p> : <ul className="divide-y divide-platforma-border">
        {rows.map(row => <li key={row.id} className="space-y-2 py-3 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2"><span className="break-words font-semibold text-platforma-text">{row.full_name}</span>
            <span className="text-platforma-subtle">{t(`medical.repStatus.${row.status}`)}</span></div>
          <p className="break-words text-platforma-text">{row.permission_labels ? row.permissions.map(code => row.permission_labels![code][language]).join(", ") : t("medical.repLabelsUnavailable")}</p>
          <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <div><dt className="text-platforma-subtle">{t("medical.repFrom")}</dt><dd>{date(row.valid_from)}</dd></div>
            <div><dt className="text-platforma-subtle">{t("medical.repUntil")}</dt><dd>{row.valid_until ? date(row.valid_until) : t("medical.repNoExpiry")}</dd></div>
          </dl>
          {canApprove && row.status !== "revoked" ? <Button size="lg" variant="secondary" onClick={() => setEdit(row)}>{t("medical.repRevoke")}</Button> : null}
        </li>)}
      </ul>}
      <div className="flex flex-wrap gap-2">
        {offset > 0 ? <Button variant="secondary" onClick={() => setOffset(value => Math.max(0, value - 25))}>{t("medical.repPrevious")}</Button> : null}
        {next !== null ? <Button variant="secondary" onClick={() => setOffset(next)}>{t("medical.repNext")}</Button> : null}
      </div>
    </>}
    <Modal title={t(edit === "new" ? "medical.repAdd" : "medical.repRevoke")} open={edit !== null} onClose={close} size="lg" closeOnBackdrop={false}>
      {edit ? <RepresentativeForm key={edit === "new" ? "new" : edit.id} patient={patient} scope={scope} relation={edit === "new" ? null : edit}
        onCancel={close} onDenied={onDenied} onSaved={() => { setOffset(0); close(); }} /> : null}
    </Modal>
  </section>;
}
