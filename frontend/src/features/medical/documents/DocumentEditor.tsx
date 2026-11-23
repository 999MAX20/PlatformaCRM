import { useEffect, useState } from "react";
import { medicalDocumentsApi as api, type DocumentAccess, type DocumentDraft, type DocumentPreview, type DocumentScope, type DocumentVersion } from "../../../api/medicalDocuments";
import { medicalTemplatesApi, type TemplateRow, type TemplateSearch as SearchFilters } from "../../../api/medicalTemplates";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Textarea } from "../../../components/ui/Textarea";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { MedicalRoleCommand, type RoleFormControl } from "../roles/MedicalRoleCommand";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";
import { TemplateSearch } from "../templates/TemplateSearch";
import { TemplateDocx } from "../templates/TemplateDocx";

export function DocumentEditor({ scope, version, control }: {
  scope: DocumentScope; version: DocumentVersion | null; control: RoleFormControl;
}) {
  const { t } = useI18n();
  const [access, setAccess] = useState<DocumentAccess | null>(null);
  const [preview, setPreview] = useState<DocumentPreview | null>(null);
  const [rows, setRows] = useState<TemplateRow[]>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const [choice, setChoice] = useState<number | null>(version?.snapshot.template_source?.version_id ?? null);
  const [before, setBefore] = useState<number | undefined>();
  const [filters, setFilters] = useState<SearchFilters>({});
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(null);
    void (async () => {
      const permissions = await api.access(scope, controller.signal);
      if (choice) {
        const source = await api.preview(scope, choice, version?.document_id, controller.signal);
        if (!controller.signal.aborted) { setPreview(source); setAccess(permissions); }
      } else {
        const page = await medicalTemplatesApi.approved(scope.business_id, before, controller.signal, filters);
        if (!controller.signal.aborted) { setRows(previous => before ? [...previous, ...page.results] : page.results); setCursor(page.next_before_id); setAccess(permissions); }
      }
    })().catch(cause => { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) control.onDenied(cause); else setError(cause); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [scope, choice, before, attempt, control.onDenied, version?.document_id, filters]);
  if (loading && (choice || !access)) return <LoadingState />;
  if (error && (choice || !access)) return <div className="space-y-3">
    <ErrorState message={getApiErrorMessage(error)} action={<Button onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} />
    {choice && !version && access ? <Button variant="secondary" onClick={() => { setChoice(null); setPreview(null); setBefore(undefined); }}>{t("medical.documents.changeTemplate")}</Button> : null}
  </div>;
  if (!access || !(version ? access.actions.update : access.actions.create)) return <p role="status">{t("medical.clinical.readOnly")}</p>;
  if (preview) return <DocumentForm scope={scope} version={version} preview={preview} control={control} />;
  return <div className="space-y-4">
    <h2 className="text-base font-semibold">{t("medical.documents.chooseTemplate")}</h2>
    <TemplateSearch approved disabled={loading} value={filters} onApply={value => { setLoading(true); setBefore(undefined); setRows([]); setCursor(null); setFilters(value); }} />
    {loading ? <LoadingState /> : null}
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} /> : null}
    {!loading && !error && !rows.length ? <p className="text-sm text-platforma-subtle">{t(Object.entries(filters).some(([key, value]) => value && (key !== "scope" || value !== "all")) ? "medical.templates.noMatches" : "medical.documents.noTemplates")}</p> : null}
    <ul className="divide-y divide-platforma-border">{rows.map(row => <li key={row.template_id} className="py-2">
      <Button size="lg" variant="secondary" disabled={loading} className="h-auto w-full whitespace-normal text-left" onClick={() => setChoice(row.version_id)}>
        <span className="min-w-0 break-words">{row.title} · {t("medical.templates.version", { revision: row.revision })}</span>
      </Button>
    </li>)}</ul>
    {cursor && !error ? <Button variant="secondary" disabled={loading} onClick={() => setBefore(cursor)}>{t("medical.templates.more")}</Button> : null}
  </div>;
}

export function DocumentForm({ scope, version, preview, control, submitDocument }: {
  scope: Pick<DocumentDraft, "business_id" | "patient_id" | "encounter_id" | "participation_id">;
  version: DocumentVersion | null; preview: DocumentPreview; control: RoleFormControl;
  submitDocument?: (payload: DocumentDraft, key: string) => Promise<unknown>;
}) {
  const { t } = useI18n();
  const template = preview.template;
  const initial = version?.snapshot.document_text ?? preview.document_text;
  const [text, setText] = useState(initial);
  const [reason, setReason] = useState("");
  const dirty = !version || text !== initial || !!reason;
  const payload = dirty ? { business_id: scope.business_id, patient_id: scope.patient_id, encounter_id: scope.encounter_id,
    expected_patient_revision: preview.patient_revision, expected_encounter_revision: preview.encounter_revision,
    expected_source_digest: preview.source_digest,
    template_version_id: template.version_id, document_text: text, reason,
    ...(scope.participation_id ? { participation_id: scope.participation_id } : {}) } : null;
  return <MedicalRoleCommand payload={payload} dirty={dirty} control={control} label={t("medical.clinical.save")}
    submit={(data, key) => submitDocument ? submitDocument(data, key) : version ? api.update(version.document_id, { ...data, expected_document_revision: version.revision }, key) : api.create(data, key)}>
    <h2 className="break-words text-base font-semibold">{template.template.title}</h2>
    <p className="text-sm text-platforma-subtle">{t("medical.documents.sourceVersion", { revision: template.revision })}</p>
    <TemplateDocx key={template.version_id} businessId={scope.business_id} versionId={template.version_id} onDenied={control.onDenied} />
    {!version && preview.missing_fields.length ? <p role="status" className="text-sm text-platforma-subtle">
      {t("medical.documents.missingFields", { count: preview.missing_fields.length })}
    </p> : null}
    {!version && preview.unknown_fields.length ? <p role="status" className="text-sm text-platforma-subtle">
      {t("medical.documents.unknownFields", { count: preview.unknown_fields.length })}
    </p> : null}
    <Textarea label={t("medical.documents.text")} value={text} rows={14} maxLength={131072} onChange={event => setText(event.target.value)} />
    <Textarea label={t("medical.templates.reason")} value={reason} rows={2} maxLength={2000} onChange={event => setReason(event.target.value)} />
  </MedicalRoleCommand>;
}
