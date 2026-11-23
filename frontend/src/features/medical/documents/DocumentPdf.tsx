import { lazy, Suspense, useEffect, useRef, useState } from "react";
import axios from "axios";
import { medicalDocumentArtifactsApi as api, type DocumentArtifact, type DocumentArtifactScope } from "../../../api/medicalDocumentArtifacts";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";
import { openDocumentPrintWindow } from "./documentPrint";
import { DocumentExportHistory } from "./DocumentExportHistory";

const PdfPreview = lazy(() => import("../files/MedicalPdfPreview"));

type DocumentPdfProps = {
  scope: DocumentArtifactScope; versionId: number; title: string; onDenied: (cause: unknown) => void;
};

export function DocumentPdf(props: DocumentPdfProps) {
  const { language } = useI18n();
  const { scope, versionId } = props;
  const identity = JSON.stringify([scope.business_id, scope.patient_id, scope.appointment_id,
    scope.participation_id, scope.correction_access_id, scope.head_branch_id, versionId, language]);
  return <DocumentPdfContent key={identity} {...props} />;
}

function DocumentPdfContent({ scope, versionId, title, onDenied }: DocumentPdfProps) {
  const { t, language } = useI18n();
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [blob, setBlob] = useState<Blob | null>(null);
  const [status, setStatus] = useState<DocumentArtifact["scan_status"] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [canExport, setCanExport] = useState(false);
  const [historyRefresh, setHistoryRefresh] = useState(0);
  const [failedAction, setFailedAction] = useState<"preview" | "download" | "print">("preview");
  const printWindow = useRef<ReturnType<typeof openDocumentPrintWindow>>(null);
  const request = useRef<AbortController | null>(null);
  const trigger = useRef<HTMLButtonElement | null>(null);
  useEffect(() => () => { request.current?.abort(); printWindow.current?.close(); }, []);
  function close() {
    request.current?.abort(); printWindow.current?.close(); printWindow.current = null;
    setOpen(false); setPending(false); setBlob(null); setError(null); setStatus(null); setCanExport(false);
    requestAnimationFrame(() => trigger.current?.focus());
  }
  async function show() {
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    setOpen(true); setPending(true); setError(null); setBlob(null); setStatus(null);
    setFailedAction("preview"); setCanExport(false);
    try {
      const result = await api.prepare(scope, versionId, language, controller.signal);
      if (controller.signal.aborted) return;
      setStatus(result.scan_status);
      setCanExport(result.can_export);
      if (result.scan_status === "clean") {
        const value = await api.preview(scope, versionId, language, controller.signal);
        if (!controller.signal.aborted) setBlob(value);
      }
    } catch (cause) {
      if (!controller.signal.aborted) {
        if (medicalRoleDenied(cause)) { close(); onDenied(cause); }
        else if (axios.isAxiosError(cause) && cause.response?.status === 423) setStatus("pending");
        else setError(cause);
      }
    } finally { if (!controller.signal.aborted) setPending(false); }
  }
  async function exportPdf(purpose: "download" | "print") {
    if (pending || !canExport) return;
    request.current?.abort(); printWindow.current?.close(); printWindow.current = null;
    const controller = new AbortController(); request.current = controller;
    setPending(true); setError(null); setFailedAction(purpose);
    try {
      if (purpose === "print") {
        printWindow.current = openDocumentPrintWindow(title, t("common.loading"));
        if (!printWindow.current) throw new Error(t("medical.documents.popupBlocked"));
      }
      const file = await api.export(scope, versionId, language, purpose, controller.signal);
      if (controller.signal.aborted) return;
      setHistoryRefresh(value => value + 1);
      if (purpose === "print") await printWindow.current?.render(file, controller.signal, t("medical.documents.print"));
      else {
        const url = URL.createObjectURL(file);
        const link = document.createElement("a"); link.href = url; link.download = `document-${versionId}.pdf`; link.click();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
    } catch (cause) {
      printWindow.current?.close(); printWindow.current = null;
      if (!controller.signal.aborted) {
        if (medicalRoleDenied(cause)) { close(); onDenied(cause); }
        else if (axios.isAxiosError(cause) && cause.response?.status === 423) { setBlob(null); setStatus("pending"); }
        else setError(cause);
      }
    } finally { if (!controller.signal.aborted) setPending(false); }
  }
  return <section className="min-w-0 space-y-3" data-testid="medical-document-pdf">
    <div className="flex flex-wrap gap-2">
      <Button ref={trigger} type="button" size="lg" variant="secondary" disabled={pending} onClick={() => void show()}>{t("medical.documents.pdfPreview")}</Button>
      {open && canExport && status === "clean" ? <>
        <Button type="button" size="lg" variant="secondary" disabled={pending} onClick={() => void exportPdf("download")}>{t("medical.documents.downloadPdf")}</Button>
        <Button type="button" size="lg" variant="secondary" disabled={pending} onClick={() => void exportPdf("print")}>{t("medical.documents.print")}</Button>
      </> : null}
      {open ? <Button type="button" size="lg" variant="secondary" onClick={close}>{t("common.close")}</Button> : null}
    </div>
    {open && pending ? <LoadingState /> : null}
    {open && error ? <ErrorState error={error} message={error instanceof Error && error.message === t("medical.documents.popupBlocked") ? error.message : getApiErrorMessage(error)} action={<Button type="button" size="lg" variant="secondary" onClick={() => void (failedAction === "preview" ? show() : exportPdf(failedAction))}>{t("common.retry")}</Button>} /> : null}
    {open && !pending && !error && status && status !== "clean" ? <div className="space-y-2" role="status">
      <p className="text-sm">{t(`medical.files.${status}`)}</p>
      <Button type="button" size="lg" variant="secondary" onClick={() => void show()}>{t("common.retry")}</Button>
    </div> : null}
    <DocumentExportHistory scope={scope} versionId={versionId} refresh={historyRefresh} onDenied={onDenied} />
    {open && blob ? <Suspense fallback={<LoadingState />}><PdfPreview blob={blob} name={title} onRetry={() => void show()} /></Suspense> : null}
  </section>;
}
