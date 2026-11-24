import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { medicalAssistantsApi as api, type AssistantWorkspace, type AssistantDraftRow, type AssistantTemplateRow } from "../../api/medicalAssistants";
import type { DocumentPreview, DocumentVersion } from "../../api/medicalDocuments";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { formatDateTime } from "../../lib/format";
import { localeByLanguage } from "../calendar/calendarConstants";
import { DocumentForm } from "./documents/DocumentEditor";
import { medicalRoleDenied } from "./roles/useMedicalRolePage";
import type { RoleDraftState } from "./roles/MedicalRoleCommand";

export function AssistantDraftWorkspace({ businessId, invitationId, guard, onDraft, onDenied }: {
  businessId: number; invitationId: number; guard: { current: RoleDraftState };
  onDraft: (value: RoleDraftState) => void; onDenied: (cause: unknown) => void;
}) {
  const { t, language } = useI18n();
  const [workspace, setWorkspace] = useState<AssistantWorkspace | null>(null);
  const [rows, setRows] = useState<AssistantDraftRow[]>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const [templates, setTemplates] = useState<AssistantTemplateRow[]>([]);
  const [templateCursor, setTemplateCursor] = useState<number | null>(null);
  const [choosing, setChoosing] = useState(false);
  const [editor, setEditor] = useState<{ preview: DocumentPreview; version: DocumentVersion | null } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState(false);
  const request = useRef<AbortController | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const origin = useRef<string | null>(null);
  const retryRead = useRef<() => void>(() => {});
  const denied = useCallback((cause: unknown) => {
    setWorkspace(null); setRows([]); setTemplates([]); setEditor(null); setChoosing(false); onDenied(cause);
  }, [onDenied]);
  const load = useCallback(async (before?: number) => {
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    retryRead.current = () => void load(before); setLoading(true); setError(null);
    try {
      const value = await api.workspace(invitationId, businessId, controller.signal);
      const page = value.actions.update ? await api.drafts(invitationId, { business_id: businessId, before_id: before }, controller.signal) : { results: [], next_before_id: null };
      if (!controller.signal.aborted) { setWorkspace(value); setRows(previous => before ? [...previous, ...page.results] : page.results); setCursor(page.next_before_id); }
    } catch (cause) { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) denied(cause); else setError(cause); } }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }, [businessId, invitationId, denied]);
  useEffect(() => { void load(); heading.current?.focus(); return () => request.current?.abort(); }, [load]);
  function leaveEditor() {
    if (guard.current.pending || (guard.current.dirty && !window.confirm(t("medical.clinical.discard")))) return;
    request.current?.abort(); setLoading(false); setError(null); setEditor(null); setChoosing(false);
    onDraft({ dirty: false, pending: false });
    requestAnimationFrame(() => { if (origin.current) document.getElementById(origin.current)?.focus(); });
  }
  const saved = useCallback(() => {
    setEditor(null); setChoosing(false); setNotice(true); onDraft({ dirty: false, pending: false }); void load();
    requestAnimationFrame(() => heading.current?.focus());
  }, [load, onDraft]);
  const control = useMemo(() => ({ guard, onDraft, onSaved: saved, onDenied: denied }), [guard, onDraft, saved, denied]);
  async function chooseTemplate(before?: number) {
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    retryRead.current = () => void chooseTemplate(before); setLoading(true); setError(null); setChoosing(true); setNotice(false);
    try {
      const page = await api.templates(invitationId, { business_id: businessId, before_id: before }, controller.signal);
      if (!controller.signal.aborted) { setTemplates(previous => before ? [...previous, ...page.results] : page.results); setTemplateCursor(page.next_before_id); }
    } catch (cause) { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) denied(cause); else setError(cause); } }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }
  async function edit(templateId?: number, row?: AssistantDraftRow) {
    if (!workspace?.encounter_id) return;
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    retryRead.current = () => void edit(templateId, row); setLoading(true); setError(null); setNotice(false);
    const scope = { business_id: businessId, patient_id: workspace.patient_id, encounter_id: workspace.encounter_id };
    try {
      const version = row ? await api.document(invitationId, { ...scope, document_id: row.id }, controller.signal) : null;
      const source = version?.snapshot.template_source?.version_id ?? templateId;
      if (!source) throw new Error(t("medical.assistants.noApprovedSource"));
      const preview = await api.preview(invitationId, { ...scope, template_version_id: source, document_id: row?.id }, controller.signal);
      if (!controller.signal.aborted) { setEditor({ preview, version }); setChoosing(false); }
    } catch (cause) { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) denied(cause); else setError(cause); } }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }
  return <section className="min-w-0 space-y-4" data-testid="assistant-drafts">
    <h2 ref={heading} tabIndex={-1} className="break-words text-lg font-semibold">{workspace?.patient_name ?? t("medical.assistants.open")}</h2>
    {workspace ? <p className="break-words text-sm text-platforma-subtle">{formatDateTime(workspace.start_at, undefined, true, localeByLanguage[language])} · {workspace.clinician_name} · {workspace.branch_name}</p> : null}
    {notice ? <p role="status">{t("medical.assistants.saved")}</p> : null}
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button size="lg" onClick={() => retryRead.current()}>{t("common.retry")}</Button>} /> : null}
    {editor && workspace?.encounter_id ? <>
      <Button size="lg" variant="secondary" onClick={leaveEditor}>{t("medical.documents.back")}</Button>
      <DocumentForm key={`${editor.preview.template.version_id}:${editor.version?.revision ?? "new"}`} scope={{ business_id: businessId, patient_id: workspace.patient_id, encounter_id: workspace.encounter_id }}
        version={editor.version} preview={editor.preview} control={control} templateExport={false} submitDocument={(payload, key) => {
          const { participation_id: _participation, ...data } = payload;
          return api.saveDocument(invitationId, { ...data, ...(editor.version ? { document_id: editor.version.document_id, expected_document_revision: editor.version.revision } : {}) }, key);
        }} />
    </> : choosing ? <>
      <Button size="lg" variant="secondary" onClick={leaveEditor}>{t("common.cancel")}</Button>
      <h3 className="text-base font-semibold">{t("medical.documents.chooseTemplate")}</h3>
      <ul className="divide-y divide-platforma-border">{templates.map(row => <li key={row.template_id} className="py-2">
        <Button size="lg" variant="secondary" className="h-auto w-full whitespace-normal text-left" disabled={loading}
          onClick={() => void edit(row.version_id)}>{row.title} · {t("medical.templates.version", { revision: row.revision })}</Button>
      </li>)}</ul>
      {!loading && !error && !templates.length ? <p className="text-sm text-platforma-subtle">{t("medical.documents.noTemplates")}</p> : null}
      {templateCursor && !error ? <Button size="lg" variant="secondary" disabled={loading} onClick={() => void chooseTemplate(templateCursor)}>{t("medical.templates.more")}</Button> : null}
    </> : workspace ? <>
      <div className="flex flex-wrap gap-3">
        {workspace.actions.create ? <Button id={`assistant-${invitationId}-create`} size="lg" disabled={loading} onClick={event => { origin.current = event.currentTarget.id; void chooseTemplate(); }}>{t("medical.documents.create")}</Button> : null}
        <Button size="lg" variant="secondary" disabled={loading} onClick={() => void load()}>{t("medical.clinical.reload")}</Button>
      </div>
      {!workspace.encounter_id ? <p role="status" className="text-sm">{t("medical.assistants.waitingEncounter")}</p> : !workspace.actions.create && !workspace.actions.update ? <p role="status">{t("medical.clinical.readOnly")}</p> : null}
      <ul className="divide-y divide-platforma-border">{rows.map(row => <li key={row.id} className="py-3">
        <Button id={`assistant-${invitationId}-document-${row.id}`} size="lg" variant="secondary" className="h-auto w-full whitespace-normal text-left" disabled={loading}
          onClick={event => { origin.current = event.currentTarget.id; void edit(undefined, row); }}>
          <span className="min-w-0 break-words">{row.title}<span className="block text-sm font-normal">{t("medical.templates.version", { revision: row.revision })} · {row.prepared_by.name}</span></span>
        </Button>
      </li>)}</ul>
      {!loading && !error && workspace.actions.update && !rows.length ? <p className="text-sm text-platforma-subtle">{t("medical.documents.empty")}</p> : null}
      {cursor && !error ? <Button size="lg" variant="secondary" disabled={loading} onClick={() => void load(cursor)}>{t("medical.templates.more")}</Button> : null}
    </> : null}
    {loading ? <LoadingState /> : null}
  </section>;
}
