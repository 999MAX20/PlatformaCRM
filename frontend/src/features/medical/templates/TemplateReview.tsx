import { useEffect, useState } from "react";
import { medicalTemplatesApi as api, type TemplateReview, type TemplateReviewSummary } from "../../../api/medicalTemplates";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Textarea } from "../../../components/ui/Textarea";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { MedicalRoleCommand, type RoleFormControl } from "../roles/MedicalRoleCommand";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";

export function TemplateReviewStatus({ review }: { review: TemplateReviewSummary | null }) {
  const { t } = useI18n();
  return <div className="space-y-2" role="status">
    <p className="text-sm font-medium">{t(`medical.templates.state.${review?.state ?? "draft"}`)}</p>
    {review?.decision_reason ? <p className="whitespace-pre-wrap break-words text-sm">{t("medical.templates.decisionReason")}: {review.decision_reason}</p> : null}
  </div>;
}

export function TemplateSubmit({ businessId, versionId, control }: { businessId: number; versionId: number; control: RoleFormControl }) {
  const { t } = useI18n();
  return <MedicalRoleCommand payload={{ business_id: businessId }} dirty={false} control={control}
    label={t("medical.templates.submitConfirm")} submit={(payload, key) => api.submit(versionId, payload, key)}>
    <p className="text-sm">{t("medical.templates.submitHint")}</p>
  </MedicalRoleCommand>;
}

export function TemplateReviewDetail({ businessId, versionId, control }: { businessId: number; versionId: number; control: RoleFormControl }) {
  const { t } = useI18n();
  const [version, setVersion] = useState<TemplateReview | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const [decision, setDecision] = useState<"approved" | "rejected" | null>(null);
  const [reason, setReason] = useState("");
  useEffect(() => {
    const controller = new AbortController(); setVersion(null); setError(null);
    void api.review(businessId, versionId, controller.signal).then(value => { if (!controller.signal.aborted) setVersion(value); })
      .catch(cause => { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) control.onDenied(cause); else setError(cause); } });
    return () => controller.abort();
  }, [businessId, versionId, attempt, control.onDenied]);
  if (error) return <ErrorState message={getApiErrorMessage(error)} action={<Button onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} />;
  if (!version) return <LoadingState />;
  const current = version.revision === version.current_revision;
  const payload = decision && (decision !== "rejected" || reason.trim()) ? { business_id: businessId, decision, reason } : null;
  return <div className="space-y-4">
    <h2 className="break-words text-base font-semibold">{version.template.title}</h2>
    <p className="text-sm text-platforma-subtle">{t("medical.templates.version", { revision: version.revision })}</p>
    <div className="whitespace-pre-wrap break-words text-sm">{version.template.text}</div>
    <TemplateReviewStatus review={version} />
    {!current ? <p role="alert" className="text-sm">{t("medical.templates.outdated")}</p> : null}
    {current && version.state === "pending" ? decision ?
      <MedicalRoleCommand payload={payload} dirty={!!reason} control={control}
        label={t(decision === "approved" ? "medical.templates.approveConfirm" : "medical.templates.rejectConfirm")}
        submit={(data, key) => api.decide(versionId, data, key)}>
        <Textarea label={t("medical.templates.decisionReason")} value={reason} required={decision === "rejected"}
          maxLength={2000} rows={3} onChange={event => setReason(event.target.value)} />
      </MedicalRoleCommand> : <div className="flex flex-wrap gap-2">
        <Button onClick={() => setDecision("approved")}>{t("medical.templates.approve")}</Button>
        <Button variant="secondary" onClick={() => setDecision("rejected")}>{t("medical.templates.reject")}</Button>
      </div> : null}
  </div>;
}
