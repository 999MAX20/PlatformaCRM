import type { ClinicalContent, ClinicalField, ClinicalPlanAccess, ClinicalPlanBookingAccess } from "../../api/medicalClinical";
import { Textarea } from "../../components/ui/Textarea";
import { useI18n } from "../../lib/i18n";
import { ClinicalPlanSteps } from "./ClinicalPlanSteps";
import { ClinicalFieldAssistance } from "./ClinicalFieldAssistance";
import type { AssistanceScope } from "../../api/medicalAssistance";

export function ClinicalSectionInput({ field, content, onChange, disabled = false, readOnly = false, planAccess, bookingAccess, assistance, compact = false }: {
  compact?: boolean;
  field: ClinicalField; content: ClinicalContent; onChange: (value: ClinicalContent) => void;
  disabled?: boolean; readOnly?: boolean;
  planAccess?: ClinicalPlanAccess;
  bookingAccess?: ClinicalPlanBookingAccess;
  assistance?: {scope:Omit<AssistanceScope,"field">;onDenied:(cause:unknown)=>void};
}) {
  const { t } = useI18n();
  const label = t(`medical.clinical.${field}`);
  const reason = content.not_applicable?.[field];
  const notApplicable = reason !== undefined;
  function toggle(checked: boolean) {
    const current = notApplicable ? reason : content[field];
    if ((current?.trim() || (field === "plan" && content.plan_steps?.length) || (field === "procedures" && content.procedure_items?.length)) && !window.confirm(t("medical.clinical.replaceSection"))) return;
    const reasons = { ...content.not_applicable };
    const next: ClinicalContent = { ...content, not_applicable: reasons };
    delete next[field];
    if (field === "plan" && checked) delete next.plan_steps;
    if (field === "procedures" && checked) delete next.procedure_items;
    if (checked) reasons[field] = "";
    else {
      delete reasons[field];
      if (!Object.keys(reasons).length) delete next.not_applicable;
    }
    onChange(next);
  }
  return <div className={compact ? "appointment-clinical-field space-y-2" : "space-y-2"}>
    <Textarea label={notApplicable ? t("medical.clinical.notApplicableReason", { field: label }) : label}
      aria-label={notApplicable ? t("medical.clinical.notApplicableReason", { field: label }) : label}
      value={notApplicable ? reason : content[field] ?? ""} disabled={disabled} readOnly={readOnly}
      rows={compact ? 2 : undefined}
      required={notApplicable} maxLength={notApplicable ? 2000 : 32768}
      onChange={event => onChange(notApplicable
        ? { ...content, not_applicable: { ...content.not_applicable, [field]: event.target.value } }
        : { ...content, [field]: event.target.value })} />
    <details open={!compact || notApplicable ? true : undefined}><summary hidden={!compact}>{t("appointments.actions")}</summary>
    {assistance&&!notApplicable&&!readOnly?<ClinicalFieldAssistance scope={{...assistance.scope,field}} text={content[field]??""} disabled={disabled}
      onAccept={text=>onChange({...content,[field]:text})} onDenied={assistance.onDenied}/>:null}
    <label className="flex min-h-11 cursor-pointer items-center gap-3 text-sm">
      <input type="checkbox" className="platforma-focus-ring h-5 w-5 shrink-0 accent-brand-600"
        checked={notApplicable} disabled={disabled || readOnly}
        aria-label={t("medical.clinical.notApplicableFor", { field: label })}
        onChange={event => toggle(event.target.checked)} />
      {t("medical.clinical.notApplicable")}
    </label>
    </details>
    {field === "plan" && !notApplicable ? <ClinicalPlanSteps content={content} onChange={onChange}
      disabled={disabled} readOnly={readOnly} planAccess={planAccess} bookingAccess={bookingAccess} /> : null}
  </div>;
}
