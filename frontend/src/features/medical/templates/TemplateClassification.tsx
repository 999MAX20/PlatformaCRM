import type { TemplateMetadata } from "../../../api/medicalTemplates";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { useI18n } from "../../../lib/i18n";
import { TemplateServices } from "./TemplateServices";

export function TemplateClassification({ businessId, value, onChange, onDenied }: {
  businessId: number; value: TemplateMetadata; onChange: (value: TemplateMetadata) => void; onDenied: (cause: unknown) => void;
}) {
  const { t } = useI18n();
  return <div className="space-y-4" data-testid="template-classification">
    <Select label={t("medical.templates.language")} value={value.language}
      options={[{ value: "", label: t("medical.templates.unspecified") }, ...(["ru", "kk", "en"] as const).map(language => ({ value: language, label: t(`language.${language}`) }))]}
      onChange={event => onChange({ ...value, language: event.target.value as TemplateMetadata["language"] })} />
    <div className="grid gap-4 sm:grid-cols-2">
      <Input label={t("medical.templates.category")} value={value.category} maxLength={255} onChange={event => onChange({ ...value, category: event.target.value })} />
      <Input label={t("medical.templates.specialty")} value={value.specialty} maxLength={255} onChange={event => onChange({ ...value, specialty: event.target.value })} />
    </div>
    <TemplateServices businessId={businessId} selected={value.services} onChange={services => onChange({ ...value, services })} onDenied={onDenied} />
  </div>;
}

export function TemplateClassificationSummary({ value }: { value?: TemplateMetadata }) {
  const { t } = useI18n();
  if (!value) return null;
  const fields = [
    [t("medical.templates.language"), value.language ? t(`language.${value.language}`) : ""],
    [t("medical.templates.category"), value.category], [t("medical.templates.specialty"), value.specialty],
    [t("medical.templates.services"), value.services.map(service => service.name).join("\n")],
  ].filter(([, text]) => text);
  if (!fields.length) return null;
  return <dl className="space-y-2 text-sm" data-testid="template-classification-summary">{fields.map(([label, text]) =>
    <div key={label}><dt className="text-platforma-subtle">{label}</dt><dd className="whitespace-pre-wrap break-words">{text}</dd></div>)}</dl>;
}
