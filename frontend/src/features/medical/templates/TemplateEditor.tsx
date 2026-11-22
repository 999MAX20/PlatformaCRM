import { useLayoutEffect, useRef, useState } from "react";
import { medicalTemplatesApi, type TemplateVersion, type TemplateMetadata } from "../../../api/medicalTemplates";
import { Input } from "../../../components/ui/Input";
import { Textarea } from "../../../components/ui/Textarea";
import { useI18n } from "../../../lib/i18n";
import { MedicalRoleCommand, type RoleFormControl } from "../roles/MedicalRoleCommand";
import { TemplateFields } from "./TemplateFields";
import { TemplateClassification } from "./TemplateClassification";

export function TemplateEditor({ businessId, version, control, api = medicalTemplatesApi }: {
  api?: typeof medicalTemplatesApi; businessId: number; version: TemplateVersion | null; control: RoleFormControl;
}) {
  const { t } = useI18n();
  const [title, setTitle] = useState(version?.template.title ?? "");
  const [text, setText] = useState(version?.template.text ?? "");
  const [reason, setReason] = useState("");
  const initialMetadata: TemplateMetadata = version?.metadata ?? { language: "", category: "", specialty: "", services: [] };
  const [metadata, setMetadata] = useState(initialMetadata);
  const [insertError, setInsertError] = useState(false);
  const textarea = useRef<HTMLTextAreaElement>(null);
  const selection = useRef({ start: text.length, end: text.length });
  const caret = useRef<number | null>(null);
  useLayoutEffect(() => {
    if (caret.current === null) return;
    textarea.current?.focus();
    textarea.current?.setSelectionRange(caret.current, caret.current);
    selection.current = { start: caret.current, end: caret.current };
    caret.current = null;
  }, [text]);
  function insert(field: string) {
    const { start, end } = selection.current;
    const token = `{{${field}}}`;
    const next = text.slice(0, start) + token + text.slice(end);
    if (next.length > 131072) { setInsertError(true); return; }
    setInsertError(false);
    if (next === text) {
      textarea.current?.focus(); textarea.current?.setSelectionRange(start + token.length, start + token.length);
      selection.current = { start: start + token.length, end: start + token.length };
    } else { caret.current = start + token.length; setText(next); }
  }
  const metadataChanged = JSON.stringify(metadata) !== JSON.stringify(initialMetadata);
  const dirty = title !== (version?.template.title ?? "") || text !== (version?.template.text ?? "") || !!reason || metadataChanged;
  const payload = title.trim() && dirty ? { business_id: businessId, title, text, reason,
    ...(metadataChanged ? { metadata: { language: metadata.language, category: metadata.category,
      specialty: metadata.specialty, service_ids: metadata.services.map(service => service.id) } } : {}) } : null;
  return <MedicalRoleCommand payload={payload} dirty={dirty} control={control} label={t("common.save")}
    submit={(data, key) => version ? api.update(version.template_id, { ...data, expected_revision: version.revision }, key) : api.create(data, key)}>
    <Input label={t("medical.templates.title")} value={title} required maxLength={255} onChange={event => setTitle(event.target.value)} />
    <TemplateClassification businessId={businessId} value={metadata} onChange={setMetadata} onDenied={control.onDenied} />
    <TemplateFields businessId={businessId} onInsert={insert} onDenied={control.onDenied} />
    <Textarea ref={textarea} label={t("medical.templates.text")} aria-label={t("medical.templates.text")} value={text} rows={12} maxLength={131072}
      error={insertError ? t("medical.fields.tooLong") : undefined}
      onSelect={event => { selection.current = { start: event.currentTarget.selectionStart, end: event.currentTarget.selectionEnd }; }}
      onChange={event => { setText(event.target.value); setInsertError(false); }} />
    <Textarea label={t("medical.templates.reason")} value={reason} rows={2} maxLength={2000} onChange={event => setReason(event.target.value)} />
  </MedicalRoleCommand>;
}
