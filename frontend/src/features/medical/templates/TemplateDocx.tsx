import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { medicalTemplatesApi as api } from "../../../api/medicalTemplates";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";

export function TemplateDocx({ businessId, versionId, onDenied }: {
  businessId: number; versionId: number; onDenied: (cause: unknown) => void;
}) {
  const { t, language } = useI18n();
  const [allowed, setAllowed] = useState(false);
  const [pending, setPending] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [retryDownload, setRetryDownload] = useState(false);
  const request = useRef<AbortController | null>(null);
  const load = useCallback(async () => {
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    setPending(true); setError(null); setAllowed(false); setRetryDownload(false);
    try {
      const value = await api.docxAccess(businessId, versionId, controller.signal);
      if (!controller.signal.aborted) setAllowed(value.can_docx);
    } catch (cause) {
      if (!controller.signal.aborted) {
        if (medicalRoleDenied(cause)) onDenied(cause); else setError(cause);
      }
    } finally { if (!controller.signal.aborted) setPending(false); }
  }, [businessId, versionId, onDenied]);
  useEffect(() => { void load(); return () => request.current?.abort(); }, [load]);
  async function download() {
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    setPending(true); setError(null); setRetryDownload(true);
    try {
      const blob = await api.downloadDocx(businessId, versionId, language, controller.signal);
      if (controller.signal.aborted) return;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url; anchor.download = "template-draft.docx";
      document.body.appendChild(anchor); anchor.click(); anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (cause) {
      if (!controller.signal.aborted) {
        if (medicalRoleDenied(cause)) { setAllowed(false); onDenied(cause); }
        else {
          if (axios.isAxiosError(cause) && cause.response?.status === 409) { setAllowed(false); setRetryDownload(false); }
          setError(cause);
        }
      }
    } finally { if (!controller.signal.aborted) setPending(false); }
  }
  if (!allowed && !pending && !error) return null;
  return <div className="min-w-0 space-y-2" data-testid="template-docx">
    {allowed ? <Button type="button" size="lg" variant="secondary" disabled={pending} onClick={() => void download()}>{t("medical.templates.downloadDocx")}</Button> : null}
    {pending ? <LoadingState /> : null}
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button type="button" size="lg" disabled={pending}
      onClick={() => void (retryDownload ? download() : load())}>{t("common.retry")}</Button>} /> : null}
  </div>;
}
