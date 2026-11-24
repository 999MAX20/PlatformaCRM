import { useEffect, useState } from "react";
import { medicalOrdersApi as api, orderKinds, medicationFields, type OrderAccess, type OrderContent, type OrderScope, type OrderVersion, type OrderPreview } from "../../../api/medicalOrders";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Textarea } from "../../../components/ui/Textarea";
import { Select } from "../../../components/ui/Select";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { MedicalRoleCommand, type RoleFormControl } from "../roles/MedicalRoleCommand";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";
import { OrderTemplatePicker } from "./OrderTemplatePicker";
import { ClinicalFieldAssistance } from "../ClinicalFieldAssistance";
import { OrderTemplateCompletion } from "./OrderTemplateCompletion";

export function OrderEditor({ scope, version, control }: { scope: OrderScope; version: OrderVersion | null; control: RoleFormControl }) {
  const { t } = useI18n();
  const [access, setAccess] = useState<OrderAccess | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setError(null); setAccess(null);
    api.access(scope, controller.signal).then(value => { if (!controller.signal.aborted) setAccess(value); })
      .catch(cause => { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) control.onDenied(cause); else setError(cause); } });
    return () => controller.abort();
  }, [scope, attempt, control.onDenied]);
  if (error) return <ErrorState message={getApiErrorMessage(error)} action={<Button onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} />;
  if (!access) return <LoadingState />;
  if (!(version ? access.actions.update && version.author_id === access.actor_id : access.actions.create)) return <p role="status">{t("medical.clinical.readOnly")}</p>;
  return <OrderForm scope={scope} access={access} version={version} control={control} />;
}

function OrderForm({ scope, access, version, control }: { scope: OrderScope; access: OrderAccess; version: OrderVersion | null; control: RoleFormControl }) {
  const { t } = useI18n();
  const [content, setContent] = useState<OrderContent>(version?.content ?? { kind: "other", text: "", medication: {} });
  const [reason, setReason] = useState("");
  const [picker, setPicker] = useState(false);
  const [source, setSource] = useState<OrderPreview | null>(null);
  const [hint, setHint] = useState<OrderPreview | null>(null);
  const [assistanceBusy, setAssistanceBusy] = useState(false);
  const provenance = source?.template_source ?? version?.template_source;
  const dirty = Boolean(source) || JSON.stringify(content) !== JSON.stringify(version?.content ?? { kind: "other", text: "", medication: {} }) || Boolean(reason);
  const payload = { business_id: scope.business_id, patient_id: scope.patient_id, encounter_id: scope.encounter_id,
    expected_patient_revision: source?.patient_revision ?? access.patient_revision, expected_encounter_revision: source?.encounter_revision ?? access.encounter_revision,
    ...(source ? { template_version_id: source.template_source.approval.version_id, expected_source_digest: source.template_source.source_digest } : {}),
    participation_id: scope.participation_id, ...(version ? { expected_order_revision: version.revision } : {}), content, reason };
  return <><MedicalRoleCommand payload={picker || assistanceBusy ? null : payload} dirty={dirty} label={t("medical.clinical.save")}
    submit={(value, key) => api.save(version?.order_id ?? null, value, key)} control={control}>
    <p role="status" className="text-sm text-platforma-subtle">{t("medical.orders.draft")}</p>
    <Button type="button" size="lg" variant="secondary" data-focus-return-id="order-template-open" onClick={() => setPicker(true)}>{t("medical.documents.chooseTemplate")}</Button>
    {provenance ? <p className="break-words" data-testid="order-template-source">{provenance.template.title} · {t("medical.templates.version", { revision: provenance.approval.revision })}</p> : null}
    <Select label={t("medical.orders.kind")} value={content.kind}
      options={orderKinds.map(kind => ({ value: kind, label: t(`medical.orders.${kind}`) }))}
      onChange={event => {
        if (content.kind === "medication" && Object.values(content.medication).some(text => text?.trim()) &&
            !window.confirm(t("medical.orders.changeKind"))) return;
        setContent({ ...content, kind: event.target.value as OrderContent["kind"], medication: {} });
      }} />
    {content.kind === "medication" ? <div className="grid min-w-0 gap-4 sm:grid-cols-2">
      {medicationFields.map(field => <Input key={field} label={t(`medical.orders.field.${field}`)} value={content.medication[field] ?? ""}
        maxLength={2000} onChange={event => setContent({ ...content, medication: { ...content.medication, [field]: event.target.value } })} />)}
    </div> : null}
    <OrderTemplateCompletion scope={scope} orderId={version?.order_id} hint={hint} text={content.text}
      onChange={text => setContent({ ...content, text })} onDismiss={() => setHint(null)} onDenied={control.onDenied}
      isSaving={() => control.guard.current.pending || assistanceBusy}
      onAccept={preview => { setContent({ ...content, text: preview.document_text }); setSource(preview); setHint(null); }} />
    <ClinicalFieldAssistance scope={{...scope,field:"order_text",expected_revision:payload.expected_encounter_revision,
      expected_patient_revision:payload.expected_patient_revision,order_id:version?.order_id,expected_order_revision:version?.revision}}
      text={content.text} disabled={picker} onBusy={setAssistanceBusy} onDenied={control.onDenied}
      onAccept={text=>setContent({...content,text})}/>
    {version ? <Textarea label={t("medical.reason")} value={reason} maxLength={2000} onChange={event => setReason(event.target.value)} /> : null}
  </MedicalRoleCommand>
    {picker ? <OrderTemplatePicker scope={scope} orderId={version?.order_id} onClose={() => setPicker(false)} onDenied={control.onDenied}
      onSuggest={preview => { setHint(preview); setPicker(false); }}
      onApply={preview => {
        if (content.text && !window.confirm(t("medical.orders.replaceText"))) return;
        setContent({ ...content, text: preview.document_text }); setSource(preview); setHint(null); setPicker(false);
      }} /> : null}
  </>;
}
