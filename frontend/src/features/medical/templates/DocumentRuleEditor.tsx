import { useState } from "react";
import { medicalDocumentRulesApi, type DocumentRuleAccess, type DocumentRuleContent, type DocumentRuleVersion } from "../../../api/medicalDocumentRules";
import { Input } from "../../../components/ui/Input";
import { Textarea } from "../../../components/ui/Textarea";
import { useI18n } from "../../../lib/i18n";
import { MedicalRoleCommand, type RoleFormControl } from "../roles/MedicalRoleCommand";
import { DocumentRuleRequirements } from "./DocumentRuleRequirements";
import { DocumentRuleTemplates } from "./DocumentRuleTemplates";
import { TemplateServices } from "./TemplateServices";

const initial = (): DocumentRuleContent => ({ name: "", docx_allowed: false, validation: "synthetic", services: [], templates: [],
  default: { required_at: "optional", required_fields: [], reviewers: ["primary_clinician"], signers: [], issuable: false } });

export function DocumentRuleEditor({ businessId, version, access, control }: {
  businessId: number; version: DocumentRuleVersion | null; access: DocumentRuleAccess; control: RoleFormControl;
}) {
  const { t } = useI18n();
  const [baseline] = useState(() => version?.content ?? initial());
  const [content, setContent] = useState(baseline);
  const [reason, setReason] = useState("");
  const dirty = JSON.stringify(content) !== JSON.stringify(baseline) || !!reason;
  const payload = content.name.trim() && reason.trim() && dirty ? { business_id: businessId, reason,
    ...(version ? { expected_revision: version.revision } : {}), template_ids: content.templates.map(item => item.id),
    content: { name: content.name, docx_allowed: content.docx_allowed, default: content.default,
      services: content.services.map(item => ({ service_id: item.id, rule: item.rule })) } } : null;
  return <MedicalRoleCommand payload={payload} dirty={dirty} control={control} label={t("common.save")}
    submit={(value, key) => medicalDocumentRulesApi.save(version?.kind_id ?? null, value, key)}>
    <Input label={t("medical.rules.name")} value={content.name} required maxLength={255} onChange={event => setContent({ ...content, name: event.target.value })} />
    <label className="flex min-h-11 items-center gap-3 text-sm"><input type="checkbox" className="h-5 w-5 shrink-0 accent-brand-600"
      checked={content.docx_allowed} onChange={event => setContent({ ...content, docx_allowed: event.target.checked })} />{t("medical.rules.docx")}</label>
    <DocumentRuleTemplates businessId={businessId} selected={content.templates} onChange={templates => setContent({ ...content, templates })} onDenied={control.onDenied} />
    <section className="space-y-4 border-t border-platforma-border pt-4"><h3 className="text-base font-semibold">{t("medical.rules.default")}</h3>
      <DocumentRuleRequirements value={content.default} access={access} onChange={value => setContent({ ...content, default: value })} /></section>
    <section className="space-y-4 border-t border-platforma-border pt-4"><h3 className="text-base font-semibold">{t("medical.rules.services")}</h3>
      <TemplateServices businessId={businessId} selected={content.services.map(({ id, name }) => ({ id, name }))} onDenied={control.onDenied}
        onChange={services => setContent({ ...content, services: services.map(item => ({ ...item,
          rule: content.services.find(row => row.id === item.id)?.rule ?? structuredClone(content.default) })) })} />
      {content.services.map(item => <details key={item.id} className="border-t border-platforma-border py-3">
        <summary className="platforma-focus-ring min-h-11 cursor-pointer break-words py-2 font-medium">{item.name}</summary>
        <DocumentRuleRequirements value={item.rule} access={access} onChange={rule => setContent({ ...content,
          services: content.services.map(row => row.id === item.id ? { ...row, rule } : row) })} />
      </details>)}
    </section>
    <Textarea label={t("medical.templates.reason")} value={reason} required maxLength={2000} rows={2} onChange={event => setReason(event.target.value)} />
  </MedicalRoleCommand>;
}
