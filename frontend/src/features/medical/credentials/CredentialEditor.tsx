import { useState } from "react";
import { medicalCredentialsApi, type CredentialContent, type CredentialProfile } from "../../../api/medicalCredentials";
import { Input } from "../../../components/ui/Input";
import { Textarea } from "../../../components/ui/Textarea";
import { useI18n } from "../../../lib/i18n";
import { MedicalRoleCommand, type RoleFormControl } from "../roles/MedicalRoleCommand";

export function CredentialEditor({ businessId, profile, control }: {
  businessId: number; profile: CredentialProfile; control: RoleFormControl;
}) {
  const { t } = useI18n();
  const initial: CredentialContent = profile.version?.content ?? (profile.member_id === null
    ? { license: "" } : { specialty: "", position: "", qualification: "" });
  const [content, setContent] = useState(initial);
  const [reason, setReason] = useState("");
  const dirty = JSON.stringify(initial) !== JSON.stringify(content) || !!reason;
  const valid = "license" in content ? !!content.license.trim() : !!content.specialty.trim() && !!content.position.trim();
  const payload = valid && (dirty || !profile.version?.confirmed_at) ? { business_id: businessId,
    member_id: profile.member_id, expected_revision: profile.current_revision, content, reason } : null;
  return <MedicalRoleCommand payload={payload} dirty={dirty} control={control}
    submit={medicalCredentialsApi.confirm} label={t("medical.credentials.confirm")}>
    <p className="text-sm text-platforma-subtle">{t("medical.credentials.internal")}</p>
    {"license" in content ? <Textarea label={t("medical.credentials.license")} value={content.license} required maxLength={4000} rows={4}
      onChange={event => setContent({ license: event.target.value })} /> : <>
      <Input label={t("medical.credentials.specialty")} value={content.specialty} required maxLength={255}
        onChange={event => setContent({ ...content, specialty: event.target.value })} />
      <Input label={t("medical.credentials.position")} value={content.position} required maxLength={255}
        onChange={event => setContent({ ...content, position: event.target.value })} />
      <Textarea label={t("medical.credentials.qualification")} value={content.qualification} maxLength={4000} rows={3}
        onChange={event => setContent({ ...content, qualification: event.target.value })} />
    </>}
    <Textarea label={t("medical.templates.reason")} value={reason} rows={2} maxLength={2000} onChange={event => setReason(event.target.value)} />
  </MedicalRoleCommand>;
}
