import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { medicalSigningApi } from "../../../api/medicalSigning";
import type { DocumentReadScope } from "../../../api/medicalDocuments";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";
const PdfPreview = lazy(() => import("../files/MedicalPdfPreview"));

export function SigningPdf({ scope, versionId, artifactId, onDenied }: {
  scope: DocumentReadScope; versionId: number; artifactId: number; onDenied: (cause: unknown) => void;
}) {
  const { t } = useI18n();
  const [blob, setBlob] = useState<Blob | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [pending, setPending] = useState(false);
  const request = useRef<AbortController | null>(null);
  const trigger = useRef<HTMLButtonElement | null>(null);
  useEffect(() => () => request.current?.abort(), []);
  function close() {
    request.current?.abort(); setBlob(null); setError(null); setPending(false);
    requestAnimationFrame(() => trigger.current?.focus());
  }
  async function show() {
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    setPending(true); setBlob(null); setError(null);
    try {
      const result = await medicalSigningApi.pdf(scope, versionId, artifactId, controller.signal);
      if (!controller.signal.aborted) setBlob(result);
    } catch (cause) {
      if (!controller.signal.aborted) {
        if (medicalRoleDenied(cause)) { close(); onDenied(cause); } else setError(cause);
      }
    } finally { if (!controller.signal.aborted) setPending(false); }
  }
  return <div className="min-w-0 space-y-3" data-testid="signing-pdf">
    <div className="flex flex-wrap gap-2">
      <Button ref={trigger} type="button" size="lg" variant="secondary" disabled={pending} onClick={() => void show()}>{t("medical.signing.preview")}</Button>
      {blob || error || pending ? <Button type="button" size="lg" variant="secondary" onClick={close}>{t("common.close")}</Button> : null}
    </div>
    {pending ? <LoadingState /> : null}
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button type="button" size="lg" onClick={() => void show()}>{t("common.retry")}</Button>} /> : null}
    {blob ? <Suspense fallback={<LoadingState />}><PdfPreview blob={blob} name={t("medical.signing.preview")} onRetry={() => void show()} /></Suspense> : null}
  </div>;
}
