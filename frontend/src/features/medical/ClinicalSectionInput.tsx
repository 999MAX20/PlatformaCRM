import type { ClinicalContent, ClinicalField } from "../../api/medicalClinical";
import { Textarea } from "../../components/ui/Textarea";
import { useI18n } from "../../lib/i18n";

export function ClinicalSectionInput({ field, content, onChange, disabled = false, readOnly = false }: {
  field: ClinicalField; content: ClinicalContent; onChange: (value: ClinicalContent) => void;
  disabled?: boolean; readOnly?: boolean;
}) {
  const { t } = useI18n();
  const label = t(`medical.clinical.${field}`);
  const reason = content.not_applicable?.[field];
  const notApplicable = reason !== undefined;
  function toggle(checked: boolean) {
    const current = notApplicable ? reason : content[field];
    if (current?.trim() && !window.confirm(t("medical.clinical.replaceSection"))) return;
    const reasons = { ...content.not_applicable };
    const next: ClinicalContent = { ...content, not_applicable: reasons };
    delete next[field];
    if (checked) reasons[field] = "";
    else {
      delete reasons[field];
      if (!Object.keys(reasons).length) delete next.not_applicable;
    }
    onChange(next);
  }
  return <div className="space-y-2">
    <Textarea label={notApplicable ? t("medical.clinical.notApplicableReason", { field: label }) : label}
      aria-label={notApplicable ? t("medical.clinical.notApplicableReason", { field: label }) : label}
      value={notApplicable ? reason : content[field] ?? ""} disabled={disabled} readOnly={readOnly}
      required={notApplicable} maxLength={notApplicable ? 2000 : 32768}
      onChange={event => onChange(notApplicable
        ? { ...content, not_applicable: { ...content.not_applicable, [field]: event.target.value } }
        : { ...content, [field]: event.target.value })} />
    <label className="flex min-h-11 cursor-pointer items-center gap-3 text-sm">
      <input type="checkbox" className="platforma-focus-ring h-5 w-5 shrink-0 accent-brand-600"
        checked={notApplicable} disabled={disabled || readOnly}
        aria-label={t("medical.clinical.notApplicableFor", { field: label })}
        onChange={event => toggle(event.target.checked)} />
      {t("medical.clinical.notApplicable")}
    </label>
  </div>;
}
