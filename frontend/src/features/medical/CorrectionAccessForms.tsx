import { useCallback, useEffect, useMemo, useState } from "react";
import { correctionAccessApi as api, type CorrectionAccess, type CorrectionScope, type CorrectionTargets, type CorrectionTargetContent } from "../../api/medicalCorrectionAccess";
import { clinicalFields, type ClinicalContent } from "../../api/medicalClinical";
import { ClinicalSectionInput } from "./ClinicalSectionInput";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { MedicalRoleCommand, type RoleFormControl } from "./roles/MedicalRoleCommand";
import { medicalRoleDenied } from "./roles/useMedicalRolePage";
import { DocumentPdf } from "./documents/DocumentPdf";
import { DocumentReview } from "./documents/DocumentReview";

export type CorrectionAction = "approve" | "reject" | "withdraw" | "complete" | "revoke";

export function CorrectionDecisionForm({ item, action, businessId, control }: {
  item: CorrectionAccess; action: CorrectionAction; businessId: number; control: RoleFormControl;
}) {
  const { t } = useI18n();
  const [reason, setReason] = useState("");
  const payload = reason.trim() ? { business_id: businessId, expected_revision: item.revision, reason } : null;
  return <MedicalRoleCommand payload={payload} dirty={Boolean(reason)} control={control} label={t(`medical.correctionAccess.${action}`)}
    submit={(value, key) => action === "approve" || action === "reject"
      ? api.review(item.id, { ...value, decision: action }, key) : api.close(item.id, { ...value, decision: action }, key)}>
    <Textarea label={t("medical.reason")} value={reason} onChange={event => setReason(event.target.value)} maxLength={2000} required />
  </MedicalRoleCommand>;
}

export function CorrectionRequestForm({ scope, control }: { scope: CorrectionScope; control: RoleFormControl }) {
  const { t, language } = useI18n();
  const [page, setPage] = useState<CorrectionTargets | null>(null);
  const [before, setBefore] = useState<number | undefined>();
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState<unknown>(null);
  const [selected, setSelected] = useState("");
  const [document, setDocument] = useState("");
  const [reason, setReason] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    setPage(null); setError(null); setSelected(""); setDocument("");
    void api.targets({ ...scope, before_id: before }, controller.signal).then(value => {
      if (!controller.signal.aborted) setPage(value);
    }).catch(cause => { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) control.onDenied(cause); else setError(cause); } });
    return () => controller.abort();
  }, [scope.business_id, scope.branch_id, scope.client_id, before, attempt, control.onDenied]);
  const target = page?.results.find(item => String(item.encounter_id) === selected);
  const doc = target?.documents.find(item => String(item.id) === document);
  const payload = target && reason.trim() && (!document || doc) ? { business_id: scope.business_id,
    encounter_id: target.encounter_id, ...(doc ? { document_id: doc.id } : {}),
    expected_patient_revision: target.patient_revision, expected_target_revision: doc?.revision ?? target.revision, reason } : null;
  return <MedicalRoleCommand payload={payload} dirty={Boolean(reason || selected)} submit={api.request} control={control} label={t("medical.correctionAccess.request")}>
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button type="button" variant="secondary" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} /> : !page ? <LoadingState /> : <>
      <Select label={t("medical.correctionAccess.encounter")} value={selected} onChange={event => { setSelected(event.target.value); setDocument(""); }} options={[
        { value: "", label: t("medical.correctionAccess.selectTarget") }, ...page.results.map(item => ({ value: item.encounter_id,
          label: `${new Date(item.started_at).toLocaleString(language)} · ${t(`medical.clinical.state.${item.state}`)}` })),
      ]} />
      {target ? <Select label={t("medical.correctionAccess.target")} value={document} onChange={event => setDocument(event.target.value)} options={[
        { value: "", label: t("medical.correctionAccess.encounter") }, ...target.documents.map(item => ({ value: item.id,
          label: `${t("medical.correctionAccess.document")} · ${new Date(item.created_at).toLocaleString(language)}` })),
      ]} /> : null}
      {!page.results.length ? <p className="text-sm text-platforma-subtle">{t("medical.correctionAccess.noTargets")}</p> : null}
      <div className="flex flex-wrap gap-2">
        {before ? <Button type="button" variant="secondary" onClick={() => setBefore(undefined)}>{t("medical.correctionAccess.firstPage")}</Button> : null}
        {page.next_before_id ? <Button type="button" variant="secondary" onClick={() => setBefore(page.next_before_id!)}>{t("medical.correctionAccess.nextPage")}</Button> : null}
      </div>
    </>}
    <Textarea label={t("medical.reason")} value={reason} onChange={event => setReason(event.target.value)} maxLength={2000} required />
  </MedicalRoleCommand>;
}


export function CorrectionDraftForm({ item, businessId, control }: { item: CorrectionAccess; businessId: number; control: RoleFormControl }) {
  const { t } = useI18n();
  const [data, setData] = useState<CorrectionTargetContent | null>(null);
  const [content, setContent] = useState<ClinicalContent>({});
  const [text, setText] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setData(null); setContent({}); setText(""); setReason(""); setError(null);
    void api.target(item.id, businessId, controller.signal).then(value => {
      if (!controller.signal.aborted) { setData(value); setContent(value.content.content ?? {}); setText(value.content.document_text ?? ""); }
    }).catch(cause => { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) control.onDenied(cause); else setError(cause); } });
    return () => controller.abort();
  }, [item.id, businessId, attempt, control.onDenied]);
  const editable = data && (data.state === "draft" || item.document_id && data.state === "finalized") && (!item.document_id || data.content.document_text !== undefined);
  const documentScope = useMemo(() => ({ business_id: businessId, patient_id: item.patient_id, correction_access_id: item.id }), [businessId, item.patient_id, item.id]);
  const reviewState = useCallback((state: string) => setData(previous => previous && previous.state !== state ? { ...previous, state } : previous), []);
  const dirty = Boolean(reason) || (data !== null && (item.document_id ? text !== data.content.document_text : JSON.stringify(content) !== JSON.stringify(data.content.content)));
  const payload = data && editable && reason.trim() ? { business_id: businessId, expected_revision: data.revision, reason,
    ...(item.document_id ? { document_text: text } : { content }) } : null;
  return <>
    {data && item.document_id && !dirty ? <DocumentReview scope={documentScope} versionId={data.version_id}
      headRequired={false} onState={reviewState} control={{ ...control, onSaved: () => setAttempt(value => value + 1) }} /> : null}
    {data && item.document_id && data.state === "draft" && data.content.document_text !== undefined && !dirty ?
      <DocumentPdf scope={{ business_id: businessId, patient_id: item.patient_id, correction_access_id: item.id }}
        versionId={data.version_id} title={t("medical.correctionAccess.document")} onDenied={control.onDenied} /> : null}
    <MedicalRoleCommand payload={payload} dirty={dirty} submit={(value, key) => api.save(item.id, value, key)} control={control} label={t("medical.clinical.save")}>
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button type="button" variant="secondary" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} /> : !data ? <LoadingState /> : <>
      {!editable ? <p role="status" className="text-sm text-platforma-subtle">{t("medical.correctionAccess.immutable")}</p> : null}
      {item.document_id && data.state === "finalized" ? <p className="text-sm text-platforma-subtle">{t("medical.documents.correctionNotice")}</p> : null}
      {item.document_id ? <Textarea label={t("medical.correctionAccess.document")} value={text} onChange={event => setText(event.target.value)} readOnly={!editable} rows={12} maxLength={131072} />
        : clinicalFields.map(field => <ClinicalSectionInput key={field} field={field} content={content}
          planAccess={{ scope: { business_id: businessId, patient_id: item.patient_id,
            encounter_id: item.encounter_id, correction_access_id: item.id }, onDenied: control.onDenied }}
          onChange={setContent} readOnly={!editable} />)}
      {editable ? <Textarea label={t("medical.reason")} value={reason} onChange={event => setReason(event.target.value)} maxLength={2000} required /> : null}
    </>}
    </MedicalRoleCommand>
  </>;
}
