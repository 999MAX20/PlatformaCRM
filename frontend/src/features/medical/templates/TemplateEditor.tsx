import { useState } from "react";
import { medicalTemplatesApi, type TemplateVersion } from "../../../api/medicalTemplates";
import { Input } from "../../../components/ui/Input";
import { Textarea } from "../../../components/ui/Textarea";
import { useI18n } from "../../../lib/i18n";
import { MedicalRoleCommand, type RoleFormControl } from "../roles/MedicalRoleCommand";

export function TemplateEditor({ businessId, version, control, api = medicalTemplatesApi }: {
  api?: typeof medicalTemplatesApi; businessId: number; version: TemplateVersion | null; control: RoleFormControl;
}) {
  const { t } = useI18n();
  const [title, setTitle] = useState(version?.template.title ?? "");
  const [text, setText] = useState(version?.template.text ?? "");
  const [reason, setReason] = useState("");
  const dirty = title !== (version?.template.title ?? "") || text !== (version?.template.text ?? "") || !!reason;
  const payload = title.trim() && dirty ? { business_id: businessId, title, text, reason } : null;
  return <MedicalRoleCommand payload={payload} dirty={dirty} control={control} label={t("common.save")}
    submit={(data, key) => version ? api.update(version.template_id, { ...data, expected_revision: version.revision }, key) : api.create(data, key)}>
    <Input label={t("medical.templates.title")} value={title} required maxLength={255} onChange={event => setTitle(event.target.value)} />
    <Textarea label={t("medical.templates.text")} value={text} rows={12} maxLength={131072} onChange={event => setText(event.target.value)} />
    <Textarea label={t("medical.templates.reason")} value={reason} rows={2} maxLength={2000} onChange={event => setReason(event.target.value)} />
  </MedicalRoleCommand>;
}
