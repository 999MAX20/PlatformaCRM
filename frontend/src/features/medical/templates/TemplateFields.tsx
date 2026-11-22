import { useEffect, useState } from "react";
import { medicalTemplatesApi } from "../../../api/medicalTemplates";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";

const labels = {
  "patient.full_name": "medical.fullName", "patient.date_of_birth": "medical.birth",
  "patient.sex": "medical.sex", "patient.address": "medical.address", "patient.iin": "medical.iin",
  "clinic.name": "medical.fields.clinicName", "clinic.legal_name": "medical.fields.clinicLegalName",
  "clinic.tax_id": "medical.fields.clinicTaxId", "clinic.address": "medical.fields.clinicAddress",
  "clinic.phone": "medical.fields.clinicPhone", "branch.name": "medical.fields.branchName",
  "branch.address": "medical.fields.branchAddress", "branch.city": "medical.fields.branchCity",
  "branch.phone": "medical.fields.branchPhone", "doctor.full_name": "medical.fields.doctorName",
  "record.number": "medical.clinical.number", "encounter.date": "medical.fields.encounterDate",
  "encounter.time": "medical.fields.encounterTime", "clinical.complaints": "medical.clinical.complaints",
  "clinical.anamnesis": "medical.clinical.anamnesis", "clinical.examination": "medical.clinical.examination",
  "clinical.diagnosis": "medical.clinical.diagnosis", "clinical.procedures": "medical.clinical.procedures",
  "clinical.plan": "medical.clinical.plan", "clinical.epicrisis": "medical.clinical.epicrisis",
} as const;

export function TemplateFields({ businessId, onInsert, onDenied }: {
  businessId: number; onInsert: (field: string) => void; onDenied: (cause: unknown) => void;
}) {
  const { t } = useI18n();
  const [fields, setFields] = useState<string[]>([]);
  const [selected, setSelected] = useState("patient.full_name");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(null);
    void medicalTemplatesApi.fields(businessId, controller.signal).then(result => {
      if (!controller.signal.aborted) setFields(result.fields);
    }).catch(cause => {
      if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) onDenied(cause); else setError(cause); }
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [businessId, attempt, onDenied]);
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={getApiErrorMessage(error)} action={
    <Button type="button" variant="secondary" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} />;
  const options = fields.filter((field): field is keyof typeof labels => Object.prototype.hasOwnProperty.call(labels, field))
    .map(field => ({ value: field, label: t(labels[field]) }));
  if (!options.length) return <p role="status" className="text-sm text-platforma-subtle">{t("medical.fields.empty")}</p>;
  const value = options.some(option => option.value === selected) ? selected : options[0].value;
  return <div className="flex flex-col gap-2 sm:flex-row sm:items-end" data-testid="medical-template-fields">
    <div className="min-w-0 flex-1"><Select label={t("medical.fields.choose")} options={options} value={value}
      onChange={event => setSelected(event.target.value)} /></div>
    <Button type="button" variant="secondary" onClick={() => onInsert(value)}>{t("medical.fields.insert")}</Button>
  </div>;
}
