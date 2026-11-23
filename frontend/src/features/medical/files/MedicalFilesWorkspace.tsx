import { lazy, Suspense, useCallback, useEffect, useImperativeHandle, useRef, useState, type Ref } from "react";
import axios from "axios";
import { medicalFilesApi as api, type MedicalFileAccess, type MedicalFileVersion, type MedicalFileWorkspaceScope, type MedicalFileUpload } from "../../../api/medicalFiles";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Textarea } from "../../../components/ui/Textarea";
import { Select } from "../../../components/ui/Select";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { formatDateTime } from "../../../lib/format";
import { localeByLanguage } from "../../calendar/calendarConstants";
import { ClinicalPlanTeeth, clinicalToothNumbers } from "../ClinicalPlanTeeth";
import { MedicalFileMetadataEditor } from "./MedicalFileMetadataEditor";
const MedicalPdfPreview = lazy(() => import("./MedicalPdfPreview"));

export type MedicalFilesState = { dirty: boolean; pending: boolean };
export type MedicalFilesNavigation = { openTooth: (tooth: number) => boolean };

export function MedicalFilesWorkspace({ scope, active, onState, onDenied, navigationRef }: {
  scope: MedicalFileWorkspaceScope; active: boolean; onState: (state: MedicalFilesState) => void;
  onDenied: (cause: unknown) => void;
  navigationRef?: Ref<MedicalFilesNavigation>;
}) {
  const { t, language } = useI18n();
  const [access, setAccess] = useState<MedicalFileAccess | null>(null);
  const [rows, setRows] = useState<MedicalFileVersion[]>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const [selected, setSelected] = useState<MedicalFileVersion | null>(null);
  const [history, setHistory] = useState<MedicalFileVersion[]>([]);
  const [historyCursor, setHistoryCursor] = useState<number | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [currentOnly, setCurrentOnly] = useState(false);
  const [toothFilter, setToothFilter] = useState<number | undefined>();
  const [editor, setEditor] = useState(false);
  const [metadataEditor, setMetadataEditor] = useState(false);
  const [metadataState, setMetadataState] = useState<MedicalFilesState>({ dirty: false, pending: false });
  const [file, setFile] = useState<File | null>(null);
  const [description, setDescription] = useState("");
  const [reason, setReason] = useState("");
  const [teeth, setTeeth] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [pending, setPending] = useState(false);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<unknown>(null);
  const [localError, setLocalError] = useState("");
  const [preview, setPreview] = useState<string | null>(null);
  const [previewBlob, setPreviewBlob] = useState<Blob | null>(null);
  const attempt = useRef<{ payload: MedicalFileUpload; key: string } | null>(null);
  const listRequest = useRef<AbortController | null>(null);
  const actionRequest = useRef<AbortController | null>(null);
  const uploadRequest = useRef<AbortController | null>(null);
  const previewUrl = useRef<string | null>(null);
  const alive = useRef(true);
  const selectedButton = useRef<HTMLButtonElement | null>(null);
  const backButton = useRef<HTMLButtonElement>(null);
  const editButton = useRef<HTMLButtonElement>(null);
  const correction = scope.correction_access_id !== undefined;
  const dirty = (editor && Boolean(file || description || reason || teeth.length)) || metadataState.dirty;
  useImperativeHandle(navigationRef, () => ({ openTooth: tooth => {
    if (!clinicalToothNumbers.includes(tooth) || pending || metadataState.pending) return false;
    if (dirty && !window.confirm(t("medical.clinical.discard"))) return false;
    setEditor(false); setMetadataEditor(false); setFile(null); setDescription(""); setReason(""); setTeeth([]); attempt.current = null;
    actionRequest.current?.abort(); clearPreview(); setSelected(null); setHistory([]); setShowHistory(false); setBusy(false);
    setCurrentOnly(false); setToothFilter(tooth); setError(null); setLocalError("");
    return true;
  } }));
  useEffect(() => { onState({ dirty, pending: pending || metadataState.pending }); }, [dirty, pending, metadataState.pending, onState]);
  const clearPreview = useCallback(() => {
    if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    previewUrl.current = null; setPreview(null); setPreviewBlob(null);
  }, []);
  const fail = useCallback((cause: unknown) => {
    if (axios.isAxiosError(cause) && [401, 403, 404].includes(cause.response?.status ?? 0)) {
      clearPreview(); setRows([]); setSelected(null); setHistory([]); setFile(null); setDescription(""); setReason(""); setTeeth([]);
      attempt.current = null; setEditor(false); onDenied(cause);
    } else setError(cause);
  }, [clearPreview, onDenied]);
  const load = useCallback(async (before?: number) => {
    listRequest.current?.abort(); const controller = new AbortController(); listRequest.current = controller;
    setLoading(true); setError(null);
    try {
      const permissions = await api.access(scope, controller.signal);
      const page = await api.list(scope, { before_id: before, encounter_id: currentOnly ? scope.encounter_id : undefined, tooth: toothFilter }, controller.signal);
      if (!controller.signal.aborted) {
        setAccess(permissions); setRows(previous => before ? [...previous, ...page.results] : page.results); setCursor(page.next_before_id);
      }
    } catch (cause) { if (!controller.signal.aborted) fail(cause); }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }, [scope, currentOnly, toothFilter, fail]);
  useEffect(() => { if (active) void load(); return () => listRequest.current?.abort(); }, [active, load]);
  useEffect(() => {
    alive.current = true;
    return () => { alive.current = false; listRequest.current?.abort(); actionRequest.current?.abort(); uploadRequest.current?.abort();
      if (previewUrl.current) URL.revokeObjectURL(previewUrl.current); onState({ dirty: false, pending: false }); };
  }, [onState]);
  useEffect(() => { if (!active) { actionRequest.current?.abort(); clearPreview(); setBusy(false); } }, [active, clearPreview]);
  useEffect(() => { if (selected) backButton.current?.focus(); }, [selected?.id]);
  function back() {
    actionRequest.current?.abort(); clearPreview(); setSelected(null); setHistory([]); setShowHistory(false); setBusy(false); setError(null);
    requestAnimationFrame(() => selectedButton.current?.focus());
  }
  function cancelEditor() {
    if (pending) { uploadRequest.current?.abort(); return; }
    if (dirty && !window.confirm(t("medical.clinical.discard"))) return;
    setEditor(false); setFile(null); setDescription(""); setReason(""); setTeeth([]); attempt.current = null; setLocalError(""); setError(null);
  }
  async function upload() {
    if (!file || !access?.record_id || pending || uploadRequest.current || (correction && !reason.trim())) return;
    if (!attempt.current) {
      const extension = file.name.split(".").pop()?.toLowerCase();
      if (!extension || !access.allowed_extensions.includes(extension) || file.size <= 0 || file.size > access.max_bytes) {
        setLocalError(t("medical.files.invalid")); return;
      }
      attempt.current = { key: crypto.randomUUID(), payload: { ...scope, record_id: access.record_id,
        encounter_id: access.encounter_id ?? undefined, file, description, teeth,
        ...(correction ? { reason } : {}),
        expected_patient_revision: access.patient_revision } };
    }
    const controller = new AbortController(); uploadRequest.current = controller;
    setPending(true); setError(null); setLocalError(""); setProgress(0);
    try {
      await api.upload(attempt.current.payload, attempt.current.key, controller.signal, setProgress);
      if (alive.current) {
        attempt.current = null; setFile(null); setDescription(""); setReason(""); setTeeth([]); setEditor(false); void load();
      }
    } catch (cause) {
      if (alive.current) {
        if (axios.isCancel(cause)) setLocalError(t("medical.files.interrupted"));
        else {
          if (axios.isAxiosError(cause) && [400, 413].includes(cause.response?.status ?? 0)) attempt.current = null;
          fail(cause);
        }
      }
    } finally { uploadRequest.current = null; if (alive.current) setPending(false); }
  }
  async function openBytes(download: boolean) {
    if (!selected || busy) return;
    actionRequest.current?.abort(); const controller = new AbortController(); actionRequest.current = controller;
    setBusy(true); setError(null); if (!download) clearPreview();
    try {
      const blob = await (download ? api.download : api.preview)(scope, selected.id, selected.version_id, controller.signal);
      if (controller.signal.aborted) return;
      const url = URL.createObjectURL(blob);
      if (download) {
        const link = document.createElement("a"); link.href = url; link.download = selected.name; link.click();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      } else { previewUrl.current = url; setPreview(url); setPreviewBlob(blob); }
    } catch (cause) { if (!controller.signal.aborted) fail(cause); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  async function loadHistory(before?: number) {
    if (!selected || busy) return;
    actionRequest.current?.abort(); const controller = new AbortController(); actionRequest.current = controller;
    setBusy(true); setError(null);
    try {
      const page = await api.history(scope, selected.id, before, controller.signal);
      if (!controller.signal.aborted) { setHistory(previous => before ? [...previous, ...page.results] : page.results);
        setHistoryCursor(page.next_before_revision); setShowHistory(true); }
    } catch (cause) { if (!controller.signal.aborted) fail(cause); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  async function refreshSelected() {
    if (!selected || busy) return;
    actionRequest.current?.abort(); const controller = new AbortController(); actionRequest.current = controller;
    setBusy(true); setError(null); clearPreview();
    try {
      const version = await api.version(scope, selected.id, selected.version_id, controller.signal);
      if (!controller.signal.aborted) setSelected(version);
    } catch (cause) { if (!controller.signal.aborted) fail(cause); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  async function selectVersion(version: MedicalFileVersion) {
    if (busy) return;
    actionRequest.current?.abort(); const controller = new AbortController(); actionRequest.current = controller;
    setBusy(true); setError(null); clearPreview();
    try {
      const current = await api.version(scope, version.id, version.version_id, controller.signal);
      if (!controller.signal.aborted) setSelected(current);
    } catch (cause) { if (!controller.signal.aborted) fail(cause); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  return <section className="min-w-0 space-y-4" data-testid="medical-files">
    {selected ? <>
      <Button ref={backButton} size="lg" variant="secondary" disabled={metadataEditor} onClick={back}>{t("medical.files.back")}</Button>
      <h3 className="break-words text-lg font-semibold">{selected.name}</h3>
      {metadataEditor ? <MedicalFileMetadataEditor scope={scope} file={selected} onState={setMetadataState} onDenied={fail}
        onCancel={() => { setMetadataEditor(false); requestAnimationFrame(() => editButton.current?.focus()); }} onSaved={version => {
          setMetadataEditor(false); setSelected(version); setHistory([]); setShowHistory(false); clearPreview(); void load();
          requestAnimationFrame(() => editButton.current?.focus());
        }} /> : null}
      <div hidden={metadataEditor} className="space-y-4">
      <p className="text-sm text-platforma-subtle">{t(`medical.files.${selected.scan_status}`)} · {selected.branch_name} · {selected.author_name}</p>
      <p className="whitespace-pre-wrap break-words text-sm">{selected.description}</p>
      <ClinicalPlanTeeth value={selected.teeth} onChange={() => {}} disabled readOnly />
      <div className="flex flex-wrap gap-2">
        <Button size="lg" variant="secondary" disabled={busy} onClick={() => void refreshSelected()}>{t("common.refresh")}</Button>
        <Button size="lg" disabled={busy || selected.scan_status !== "clean"} onClick={() => void openBytes(false)}>{t("medical.files.preview")}</Button>
        {access?.actions.export ? <Button size="lg" variant="secondary" disabled={busy || selected.scan_status !== "clean"} onClick={() => void openBytes(true)}>{t("medical.files.download")}</Button> : null}
        <Button size="lg" variant="secondary" disabled={busy} onClick={() => void loadHistory()}>{t("medical.files.history")}</Button>
        {selected.actions?.edit_metadata ? <Button ref={editButton} size="lg" variant="secondary" disabled={busy} onClick={() => { clearPreview(); setError(null); setMetadataEditor(true); }}>{t("medical.edit")}</Button> : null}
      </div>
      {preview ? selected.content_type === "application/pdf" && previewBlob ? <Suspense fallback={<LoadingState />}><MedicalPdfPreview blob={previewBlob} name={selected.name} onRetry={() => void openBytes(false)} /></Suspense> :
        <img src={preview} alt={selected.name} className="max-h-[60dvh] w-full object-contain" width={1200} height={900} /> : null}
      {showHistory ? <div className="space-y-3">{history.map(version => <div key={version.version_id} className="border-t border-platforma-border pt-3">
        <Button size="lg" variant="secondary" disabled={busy} onClick={() => void selectVersion(version)}>{t("medical.clinical.revision")} {version.revision}</Button>
        <p className="text-sm text-platforma-subtle">{formatDateTime(version.created_at, undefined, true, localeByLanguage[language])} · {version.author_name}</p>
        <p className="whitespace-pre-wrap break-words text-sm">{version.reason}</p>
      </div>)}{historyCursor ? <Button size="lg" variant="secondary" disabled={busy} onClick={() => void loadHistory(historyCursor)}>{t("common.showMore")}</Button> : null}</div> : null}
      </div>
    </> : <>
      <div className="flex flex-wrap items-end gap-3">
        {access?.actions.upload && !editor ? <Button size="lg" onClick={() => { setEditor(true); setError(null); }}>{t("medical.files.upload")}</Button> : null}
        <Button size="lg" variant="secondary" disabled={loading || pending} onClick={() => void load()}>{t("common.refresh")}</Button>
        <Select label={t("medical.tooth.tooth")} value={toothFilter ?? ""} disabled={pending || editor}
          onChange={event => setToothFilter(event.target.value ? Number(event.target.value) : undefined)} options={[
            { value: "", label: t("common.all") }, ...clinicalToothNumbers.map(tooth => ({ value: tooth, label: `${t("medical.tooth.tooth")} ${tooth}` }))]} />
        {scope.encounter_id && !correction ? <Select label={t("medical.clinical.note")} value={currentOnly ? "current" : "all"}
          onChange={event => setCurrentOnly(event.target.value === "current")} options={[
            { value: "all", label: t("medical.files.allEncounters") }, { value: "current", label: t("medical.files.currentEncounter") }]} /> : null}
      </div>
      {editor && access ? <form className="space-y-4 rounded-control border border-platforma-border p-3 sm:p-4" onSubmit={event => { event.preventDefault(); void upload(); }}>
        <Input type="file" label={t("medical.files.file")} accept={access.allowed_extensions.map(value => `.${value}`).join(",")}
          disabled={pending || Boolean(attempt.current)} onChange={event => { setFile(event.target.files?.[0] ?? null); setLocalError(""); }} />
        <p className="text-sm text-platforma-subtle">{t("medical.files.limits", { formats: access.allowed_extensions.join(", ").toUpperCase(), size: access.max_bytes / 1048576 })}</p>
        <Textarea label={t("medical.files.description")} value={description} maxLength={4000} disabled={pending || Boolean(attempt.current)} onChange={event => setDescription(event.target.value)} />
        {correction ? <Textarea label={t("medical.reason")} value={reason} maxLength={2000} required
          disabled={pending || Boolean(attempt.current)} onChange={event => setReason(event.target.value)} /> : null}
        <ClinicalPlanTeeth value={teeth} onChange={setTeeth} disabled={pending || Boolean(attempt.current)} readOnly={false} />
        {pending ? <progress className="w-full" value={progress} max={1} aria-label={t("medical.files.upload")} /> : null}
        {localError ? <p role="alert" className="text-sm">{localError}</p> : null}
        <div className="flex flex-wrap gap-2"><Button type="submit" size="lg" isLoading={pending} disabled={!file || !access.actions.upload || (correction && !reason.trim())}>{t(attempt.current ? "common.retry" : "medical.files.upload")}</Button>
          <Button type="button" size="lg" variant="secondary" onClick={cancelEditor}>{t("common.cancel")}</Button></div>
      </form> : null}
      {!editor && !loading && !rows.length && !error ? <p className="py-4 text-sm text-platforma-subtle">{t("medical.files.empty")}</p> : null}
      <ul className="divide-y divide-platforma-border">{rows.map(row => <li key={row.id} className="py-3">
        <Button size="lg" variant="ghost" className="max-w-full justify-start whitespace-normal text-left [overflow-wrap:anywhere]" disabled={editor || loading || busy}
          onClick={event => { selectedButton.current = event.currentTarget; void selectVersion(row); }}>{row.name}</Button>
        <p className="break-words text-sm text-platforma-subtle">{t(`medical.files.${row.scan_status}`)} · {formatDateTime(row.created_at, undefined, true, localeByLanguage[language])} · {row.branch_name}</p>
        {row.teeth.length ? <p className="text-sm">{t("medical.plan.teeth")}: {row.teeth.join(", ")}</p> : null}
      </li>)}</ul>
      {cursor ? <Button size="lg" variant="secondary" disabled={loading} onClick={() => void load(cursor)}>{t("common.showMore")}</Button> : null}
    </>}
    {loading || busy ? <LoadingState /> : null}
    {error ? <ErrorState message={getApiErrorMessage(error)} /> : null}
  </section>;
}
