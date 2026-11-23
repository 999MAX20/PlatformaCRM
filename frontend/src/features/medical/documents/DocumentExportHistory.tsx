import { useCallback, useEffect, useId, useRef, useState } from "react";
import { medicalDocumentArtifactsApi as api, type DocumentArtifactScope, type DocumentExportEvent } from "../../../api/medicalDocumentArtifacts";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { formatDateTime } from "../../../lib/format";
import { localeByLanguage } from "../../calendar/calendarConstants";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";

export function DocumentExportHistory({ scope, versionId, refresh, onDenied }: {
  scope: DocumentArtifactScope; versionId: number; refresh: number; onDenied: (cause: unknown) => void;
}) {
  const { t, language } = useI18n();
  const contentId = useId();
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<DocumentExportEvent[]>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const request = useRef<AbortController | null>(null);
  const failedCursor = useRef<number | undefined>(undefined);
  const load = useCallback(async (before?: number) => {
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    setPending(true); setError(null); failedCursor.current = before;
    if (before === undefined) { setRows([]); setCursor(null); }
    try {
      const page = await api.history(scope, versionId, before, controller.signal);
      if (!controller.signal.aborted) {
        setRows(current => before === undefined ? page.results : [...current, ...page.results]);
        setCursor(page.next_before_id);
      }
    } catch (cause) {
      if (!controller.signal.aborted) {
        if (medicalRoleDenied(cause)) { setRows([]); setCursor(null); onDenied(cause); }
        else setError(cause);
      }
    } finally { if (!controller.signal.aborted) setPending(false); }
  }, [scope, versionId, onDenied]);
  useEffect(() => {
    if (open) void load();
    return () => request.current?.abort();
  }, [open, refresh, load]);
  return <section className="min-w-0 space-y-3" data-testid="document-export-history">
    <Button type="button" size="lg" variant="secondary" aria-expanded={open} aria-controls={contentId} onClick={() => setOpen(value => !value)}>{t("medical.documents.exportHistory")}</Button>
    {open ? <div id={contentId} className="space-y-3">
      {rows.length ? <ul className="divide-y divide-platforma-border">
        {rows.map(row => <li key={row.id} className="space-y-1 py-3 text-sm">
          <div className="flex flex-wrap justify-between gap-2"><span className="font-medium">{t(`medical.documents.${row.action}`)}</span><span>{t("medical.templates.version").replace("{revision}", String(row.revision))}</span></div>
          <p className="break-words text-platforma-subtle">{row.actor.name || t("medical.clinical.authorUnknown")} · {formatDateTime(row.created_at, undefined, true, localeByLanguage[language])}</p>
        </li>)}
      </ul> : null}
      {!pending && !error && !rows.length ? <p className="text-sm text-platforma-subtle">{t("medical.documents.exportHistoryEmpty")}</p> : null}
      {pending ? <LoadingState /> : null}
      {error ? <ErrorState error={error} message={getApiErrorMessage(error)} action={<Button type="button" size="lg" variant="secondary" onClick={() => void load(failedCursor.current)}>{t("common.retry")}</Button>} /> : null}
      {!error && cursor !== null ? <Button type="button" size="lg" variant="secondary" disabled={pending} onClick={() => void load(cursor)}>{t("common.showMore")}</Button> : null}
    </div> : null}
  </section>;
}
