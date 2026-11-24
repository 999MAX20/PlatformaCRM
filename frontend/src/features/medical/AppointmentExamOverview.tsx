import { useRef, useState, type ReactNode } from "react";
import { Expand, ChevronRight, AlertTriangle } from "lucide-react";
import { clinicalFields, type ClinicalContent, type ClinicalField } from "../../api/medicalClinical";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { useI18n } from "../../lib/i18n";
import { AppointmentTreatmentTable } from "./AppointmentTreatmentTable";

type Section = ClinicalField | "additional";
const additional: ClinicalField[] = ["anamnesis", "allergies", "contraindications", "examination", "diagnosis", "epicrisis"];

export function AppointmentExamOverview({ content, onChange, renderField, chart, disabled, readOnly, onEditing }: {
  content: ClinicalContent; onChange: (content: ClinicalContent) => void;
  renderField: (field: ClinicalField, value: ClinicalContent, change: (value: ClinicalContent) => void) => ReactNode;
  chart?: ReactNode; disabled: boolean; readOnly: boolean; onEditing: (value: boolean) => void;
}) {
  const { t } = useI18n();
  const [section, setSection] = useState<Section | null>(null);
  const [draft, setDraft] = useState<ClinicalContent>({});
  const initial = useRef("");
  const modalForm = useRef<HTMLFormElement>(null);
  function open(next: Section) {
    const copy = structuredClone(content);
    initial.current = JSON.stringify(copy);
    setDraft(copy); setSection(next); onEditing(true);
  }
  function close() {
    if (JSON.stringify(draft) !== initial.current && !window.confirm(t("medical.clinical.discard"))) return;
    setSection(null); onEditing(false);
  }
  const title = section === "additional" ? t("medical.page.additional") : section ? t(`medical.clinical.${section}`) : "";
  const preview = (field: ClinicalField) => content.not_applicable?.[field] !== undefined
    ? `${t("medical.clinical.notApplicable")}: ${content.not_applicable[field]}`
    : content[field] || t("medical.clinical.notRecorded");
  return <>
    {(["allergies", "contraindications"] as const).filter(field => content[field]?.trim()).map(field =>
      <div className="appointment-warning" key={field}><AlertTriangle size={20} aria-hidden /><strong>{t(`medical.clinical.${field}`)}:</strong><span>{content[field]}</span></div>)}
    <section className="appointment-exam-card">
      <h2>{t("medical.page.exam")}</h2>
      <button type="button" className="appointment-complaints platforma-focus-ring" onClick={() => open("complaints")} disabled={disabled}>
        <strong>{t("medical.clinical.complaints")}</strong><span>{preview("complaints")}</span><Expand size={18} aria-hidden />
      </button>
      {chart}
      <button type="button" className="appointment-additional platforma-focus-ring" onClick={() => open("additional")} disabled={disabled}>
        {t("medical.page.additional")}<ChevronRight size={18} aria-hidden />
      </button>
    </section>
    <AppointmentTreatmentTable content={content} onChange={onChange} disabled={disabled} readOnly={readOnly} onEditing={onEditing} onLegacy={() => open("procedures")} />
    <button type="button" className="appointment-plan-summary platforma-focus-ring" disabled={disabled} onClick={() => open("plan")}>
      <strong>{t("medical.page.plan")}</strong><span>{content.plan_steps?.map(step => step.description).filter(Boolean).join(" · ") || t("medical.clinical.notRecorded")}</span><ChevronRight size={18} />
    </button>
    <section className="appointment-recommendations"><strong>{t("medical.page.recommendations")}</strong>
      <button type="button" className="platforma-focus-ring appointment-field-preview" disabled={disabled} onClick={() => open("plan")}>{preview("plan")}</button>
    </section>
    <Modal open={section !== null} title={title} onClose={close} closeOnBackdrop={false} size={section === "plan" ? "lg" : "md"}
      className="appointment-field-modal" testId="appointment-field-modal" footer={<>
        <Button type="button" variant="secondary" onClick={close}>{t("common.cancel")}</Button>
        {!readOnly && <Button type="button" onClick={() => {
          if (!modalForm.current?.reportValidity()) return;
          onChange(draft); setSection(null); onEditing(false);
        }}>{t("medical.page.apply")}</Button>}
      </>}>
      <form ref={modalForm} onSubmit={event => event.preventDefault()} className="space-y-4">
        {clinicalFields.filter(field => section === "additional" ? additional.includes(field) : field === section)
          .map(field => <div key={field}>{renderField(field, draft, setDraft)}</div>)}
      </form>
    </Modal>
  </>;
}
