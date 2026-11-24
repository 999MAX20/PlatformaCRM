import { useEffect, useImperativeHandle, useRef, useState, type Ref } from "react";
import axios from "axios";
import { medicalClinicalApi, type ClientClinicalAppointments } from "../../api/medicalClinical";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { formatDateTime } from "../../lib/format";
import { localeByLanguage } from "../calendar/calendarConstants";
import { ClinicalAppointmentEntry, type ClinicalEntryHandle } from "./ClinicalAppointmentEntry";
import { ClinicalParticipationEntry } from "./ClinicalParticipationEntry";
import { HeadDocumentsWorkspace } from "./documents/DocumentWorkspace";

export function ClientClinicalEntry({ businessId, branchId, clientId, embedded = false, navigationRef, onDirtyChange, initialTab }: {
  initialTab?: "documents"; businessId: number; branchId: number; clientId: number; embedded?: boolean; navigationRef?: Ref<ClinicalEntryHandle>; onDirtyChange?: (dirty: boolean) => void;
}) {
  const { t, language } = useI18n();
  const [data, setData] = useState<ClientClinicalAppointments | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [cursor, setCursor] = useState<number | undefined>();
  const [selected, setSelected] = useState("");
  const [attempt, setAttempt] = useState(0);
  const clinical = useRef<ClinicalEntryHandle>(null);
  useImperativeHandle(navigationRef, () => ({ beforeLeave: () => clinical.current?.beforeLeave() ?? Promise.resolve(true) }));
  async function navigate(action: () => void) {
    if (await (clinical.current?.beforeLeave() ?? Promise.resolve(true))) action();
  }
  useEffect(() => {
    const controller = new AbortController();
    setData(null); setError(null); setSelected("");
    medicalClinicalApi.clientAppointments({ business_id: businessId, branch_id: branchId,
      client_id: clientId, before_id: cursor }, controller.signal)
      .then(value => { if (!controller.signal.aborted) { setData(value); if (value.results.length === 1) setSelected(String(value.results[0].id));
        else if (!value.results.length && value.participation) setSelected("participation");
        else if (!value.results.length && value.head_documents) setSelected("head-documents"); } })
      .catch(cause => { if (!controller.signal.aborted) setError(cause); });
    return () => controller.abort();
  }, [businessId, branchId, clientId, cursor, attempt]);
  if (axios.isAxiosError(error) && [401, 403, 404].includes(error.response?.status ?? 0)) return embedded ? <p role="status">{t("medical.denied")}</p> : null;
  if (error) return <ErrorState message={getApiErrorMessage(error)} action={<Button size="lg" variant="secondary" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} />;
  if (!data) return <LoadingState />;
  return <div className="min-w-0 space-y-3" data-testid="client-clinical-entry">
    {data.results.length > 0 || (data.participation && data.head_documents) ? <Select label={t(data.participation || data.head_documents ? "medical.clinical.title" : "medical.clientEntry.appointment")} value={selected}
      onChange={event => { const next = event.target.value; void navigate(() => setSelected(next)); }} options={[
        { value: "", label: t("medical.clientEntry.select") },
        ...(data.participation ? [{ value: "participation", label: t("medical.participation.title") }] : []),
        ...(data.head_documents ? [{ value: "head-documents", label: t("medical.documents.title") }] : []),
        ...data.results.map(item => ({ value: item.id, label: formatDateTime(item.start_at, undefined, true, localeByLanguage[language]) })),
    ]} /> : !data.participation && !data.head_documents ? <p className="text-sm text-platforma-subtle">{t("medical.clientEntry.empty")}</p> : null}
    <div className="flex flex-wrap gap-2">
      {cursor !== undefined ? <Button size="lg" variant="secondary" onClick={() => void navigate(() => setCursor(undefined))}>{t("medical.clinical.newest")}</Button> : null}
      {data.next_before_id !== null ? <Button size="lg" variant="secondary" onClick={() => void navigate(() => setCursor(data.next_before_id!))}>{t("medical.clinical.older")}</Button> : null}
    </div>
    {data.results.some(item => String(item.id) === selected) ?
      <ClinicalAppointmentEntry key={`${businessId}:${clientId}:${branchId}:${selected}`} businessId={businessId} appointmentId={Number(selected)} embedded={embedded} initialTab={initialTab} navigationRef={clinical} onDirtyChange={onDirtyChange} /> : null}
    {selected === "participation" && data.participation ? <ClinicalParticipationEntry key={`participation:${data.participation.id}`}
      businessId={businessId} patientId={data.participation.patient_id} participationId={data.participation.id}
      navigationRef={clinical} onDirtyChange={onDirtyChange} onDenied={setError} /> : null}
    {selected === "head-documents" && data.head_documents ? <HeadDocumentsWorkspace businessId={businessId}
      patientId={data.head_documents.patient_id} branchId={branchId} onDenied={setError} /> : null}
  </div>;
}
