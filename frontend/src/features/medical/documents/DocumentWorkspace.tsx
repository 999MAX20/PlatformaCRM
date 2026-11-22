import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { medicalDocumentsApi as api, type DocumentAccess, type DocumentRow, type DocumentVersion, type DocumentScope, type DocumentRevision } from "../../../api/medicalDocuments";
import type { AppointmentClinicalContext } from "../../../api/medicalClinical";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Modal } from "../../../components/ui/Modal";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { formatDateTime } from "../../../lib/format";
import { localeByLanguage } from "../../calendar/calendarConstants";
import { useUnsavedEntryWarning } from "../../auth/useUnsavedEntryWarning";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";
import type { RoleDraftState } from "../roles/MedicalRoleCommand";
import { DocumentEditor } from "./DocumentEditor";

export function DocumentWorkspace({ context, active, onEditor, canEdit }: {
  context: AppointmentClinicalContext; active: boolean; onEditor: (open: boolean) => void; canEdit: () => boolean;
}) {
  const { t } = useI18n();
  const scope = useMemo<DocumentScope>(() => ({ business_id: context.business_id, patient_id: context.patient.id,
    appointment_id: context.appointment.id, encounter_id: context.encounter!.id }), [context]);
  const [rows, setRows] = useState<DocumentRow[]>([]);
  const [access, setAccess] = useState<DocumentAccess | null>(null);
  const [cursor, setCursor] = useState<number | null>(null);
  const [selected, setSelected] = useState<DocumentRow | null>(null);
  const [editor, setEditor] = useState<"create" | DocumentVersion | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [draft, setDraft] = useState<RoleDraftState>({ dirty: false, pending: false });
  const guard = useRef<RoleDraftState>({ dirty: false, pending: false });
  const request = useRef<AbortController | null>(null);
  const list = useRef<HTMLDivElement>(null);
  const selectedButton = useRef<HTMLButtonElement | null>(null);
  const backButton = useRef<HTMLButtonElement>(null);
  const editorFocus = useRef("medical-document-create");
  const scrollPosition = useRef<{ element: HTMLElement; top: number }[]>([]);
  useUnsavedEntryWarning(draft.dirty || draft.pending);
  const denied = useCallback((cause: unknown) => {
    setRows([]); setSelected(null); setAccess(null); setEditor(null); setError(cause);
    guard.current = { dirty: false, pending: false }; setDraft(guard.current); onEditor(false);
  }, [onEditor]);
  const load = useCallback(async (before?: number) => {
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    setLoading(true); setError(null);
    try {
      const permissions = await api.access(scope, controller.signal);
      const page = await api.list(scope, before, controller.signal);
      if (!controller.signal.aborted) { setAccess(permissions); setRows(previous => before ? [...previous, ...page.results] : page.results); setCursor(page.next_before_id); }
    } catch (cause) { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) denied(cause); else setError(cause); } }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }, [scope, denied]);
  useEffect(() => { if (active) void load(); return () => request.current?.abort(); }, [active, load]);
  useEffect(() => () => onEditor(false), [onEditor]);
  useEffect(() => { if (selected && window.matchMedia("(max-width: 1023px)").matches) backButton.current?.focus(); }, [selected]);
  function openEditor(value: "create" | DocumentVersion) {
    if (!canEdit()) return;
    editorFocus.current = value === "create" ? "medical-document-create" : "medical-document-edit";
    setEditor(value); onEditor(true);
  }
  function closeEditor() {
    if (guard.current.pending || (guard.current.dirty && !window.confirm(t("medical.clinical.discard")))) return;
    setEditor(null); onEditor(false);
  }
  function saved() { editorFocus.current = "medical-document-create"; setEditor(null); onEditor(false); setSelected(null); void load(); }
  function select(row: DocumentRow, button: HTMLButtonElement) {
    selectedButton.current = button;
    scrollPosition.current = [];
    for (let element = list.current?.parentElement; element; element = element.parentElement) {
      if (element.scrollHeight > element.clientHeight) scrollPosition.current.push({ element, top: element.scrollTop });
    }
    setSelected(row);
  }
  function back() {
    setSelected(null);
    requestAnimationFrame(() => {
      for (const { element, top } of scrollPosition.current) element.scrollTop = top;
      selectedButton.current?.focus({ preventScroll: true });
    });
  }
  return <section className="min-w-0 space-y-4" data-testid="medical-documents">
    <div className="flex flex-wrap gap-2">
      {access?.actions.create ? <Button id="medical-document-create" size="lg" disabled={loading} onClick={() => openEditor("create")}>{t("medical.documents.create")}</Button> : null}
      <Button size="lg" variant="secondary" disabled={loading} onClick={() => { setSelected(null); void load(); }}>{t("medical.clinical.reload")}</Button>
    </div>
    {error ? <ErrorState message={medicalRoleDenied(error) ? t("medical.denied") : getApiErrorMessage(error)} action={<Button onClick={() => void load()}>{t("common.retry")}</Button>} /> : null}
    <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(180px,1fr)_minmax(0,2fr)]">
      <div ref={list} className={selected ? "hidden min-w-0 lg:block" : "min-w-0"}>
        <ul className="divide-y divide-platforma-border">{rows.map(row => <li key={row.document_id} className="py-3">
          <Button size="lg" variant="secondary" disabled={loading} className="h-auto w-full whitespace-normal text-left" aria-pressed={selected?.document_id === row.document_id}
            onClick={event => select(row, event.currentTarget)}>
            <span className="min-w-0 break-words">{row.title}<span className="block text-sm font-normal">{t("medical.templates.version", { revision: row.revision })}</span></span>
          </Button>
        </li>)}</ul>
        {loading ? <LoadingState /> : !error && !rows.length ? <p className="text-sm text-platforma-subtle">{t("medical.documents.empty")}</p> : null}
        {cursor && !error ? <Button size="lg" variant="secondary" disabled={loading} onClick={() => void load(cursor)}>{t("medical.templates.more")}</Button> : null}
      </div>
      {selected ? <div className="min-w-0 space-y-4">
        <Button ref={backButton} size="lg" variant="secondary" onClick={back}>{t("medical.documents.back")}</Button>
        <DocumentDetail key={selected.version_id} scope={scope} row={selected} canUpdate={!!access?.actions.update} onEdit={openEditor} onDenied={denied} />
      </div> : null}
    </div>
    <Modal open={editor !== null} onClose={closeEditor} size="lg" closeOnBackdrop={false} testId="medical-document-editor"
      focusReturnId={editorFocus.current}
      title={t(editor === "create" ? "medical.documents.create" : "medical.documents.edit")}>
      {editor ? <div className="space-y-4">
        <p className="break-words text-sm">{t("medical.fullName")}: {context.patient.full_name}</p>
        <DocumentEditor scope={scope} version={editor === "create" ? null : editor}
          control={{ guard, onDraft: setDraft, onSaved: saved, onDenied: denied }} />
      </div> : null}
    </Modal>
  </section>;
}

function DocumentDetail({ scope, row, canUpdate, onEdit, onDenied }: {
  scope: DocumentScope; row: DocumentRow; canUpdate: boolean; onEdit: (version: DocumentVersion) => void; onDenied: (cause: unknown) => void;
}) {
  const { t, language } = useI18n();
  const [version, setVersion] = useState<DocumentVersion | null>(null);
  const [versions, setVersions] = useState<DocumentRevision[]>([]);
  const [current, setCurrent] = useState(row.revision);
  const [cursor, setCursor] = useState<number | null>(null);
  const [versionId, setVersionId] = useState(row.version_id);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const [historyError, setHistoryError] = useState<unknown>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const historyRequest = useRef<AbortController | null>(null);
  const readScope = useMemo(() => { const { encounter_id: _, ...value } = scope; return value; }, [scope]);
  const history = useCallback(async (before?: number) => {
    historyRequest.current?.abort(); const controller = new AbortController(); historyRequest.current = controller;
    setHistoryLoading(true); setHistoryError(null);
    try {
      const page = await api.history(readScope, row.document_id, before, controller.signal);
      if (!controller.signal.aborted) { setVersions(previous => before ? [...previous, ...page.results] : page.results); setCursor(page.next_before_revision); setCurrent(page.current_revision); }
    } catch (cause) { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) onDenied(cause); else setHistoryError(cause); } }
    finally { if (!controller.signal.aborted) setHistoryLoading(false); }
  }, [readScope, row.document_id, onDenied]);
  useEffect(() => { void history(); return () => historyRequest.current?.abort(); }, [history]);
  useEffect(() => {
    const controller = new AbortController(); setVersion(null); setError(null);
    void api.version(readScope, versionId, controller.signal).then(value => { if (!controller.signal.aborted) setVersion(value); })
      .catch(cause => { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) onDenied(cause); else setError(cause); } });
    return () => controller.abort();
  }, [readScope, versionId, attempt, onDenied]);
  return <div className="min-w-0 space-y-4" data-testid="medical-document-detail">
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} /> : !version ? <LoadingState /> : <>
      <h2 className="break-words text-lg font-semibold">{version.snapshot.template.title}</h2>
      <p className="break-words text-sm text-platforma-subtle">{t("medical.templates.version", { revision: version.revision })} · {version.snapshot.prepared_by.name} · {formatDateTime(version.created_at, undefined, true, localeByLanguage[language])}</p>
      <p className="text-sm">{t(version.state === "draft" ? "medical.clinical.state.draft" : "medical.documents.recorded")}</p>
      <div className="whitespace-pre-wrap break-words text-sm" data-testid="medical-document-text">{version.snapshot.document_text ?? version.snapshot.template.text}</div>
      {version.snapshot.reason ? <p className="whitespace-pre-wrap break-words text-sm">{t("medical.templates.reason")}: {version.snapshot.reason}</p> : null}
      {canUpdate && !historyError && !historyLoading && version.state === "draft" && version.revision === current && version.snapshot.template_source ?
        <Button id="medical-document-edit" size="lg" onClick={() => onEdit(version)}>{t("medical.documents.edit")}</Button> : null}
    </>}
    <section aria-label={t("medical.templates.history")} className="space-y-2">
      <h3 className="text-base font-semibold">{t("medical.templates.history")}</h3>
      <div className="flex flex-wrap gap-2">{versions.map(item => <Button key={item.version_id} size="lg" variant="secondary" aria-pressed={versionId === item.version_id}
        onClick={() => setVersionId(item.version_id)}>{t("medical.templates.version", { revision: item.revision })}</Button>)}</div>
      {historyLoading ? <LoadingState /> : null}
      {historyError ? <ErrorState message={getApiErrorMessage(historyError)} action={<Button onClick={() => void history()}>{t("common.retry")}</Button>} /> : null}
      {cursor && !historyError ? <Button size="lg" variant="secondary" disabled={historyLoading} onClick={() => void history(cursor)}>{t("medical.templates.more")}</Button> : null}
    </section>
  </div>;
}
