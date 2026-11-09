import { X } from "lucide-react";
import { useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { normalizeAppError } from "../../api/appError";
import { NotificationPortal, NotificationPresence, restoreNoticeFocus } from "../../components/notifications/NotificationHost";
import { RecoveryDetails } from "../../components/ui/RecoveryDetails";
import { StatusNotice, appErrorNoticeTone } from "../../components/ui/StatusNotice";
import { useI18n } from "../../lib/i18n";
import { canShowSupportDetails } from "../../components/actions/actionFeedbackPolicy";

export function ImportErrorNotice({ error, message, action }: { error: unknown; message?: string; action?: ReactNode }) {
  const { t } = useI18n();
  const appError = normalizeAppError(error);
  const [dismissed, setDismissed] = useState<unknown>();
  const card = useRef<HTMLDivElement>(null);
  const opener = useRef(document.activeElement instanceof HTMLElement ? document.activeElement : null);
  const scannerUnavailable = appError.code === "file_scan_unavailable";
  useLayoutEffect(() => {
    const node = card.current;
    return () => restoreNoticeFocus(node, opener.current);
  }, []);
  return <NotificationPortal group="notifications"><NotificationPresence>
    {dismissed !== error ? <div ref={card}>
      <StatusNotice data-testid="import-error-notice" className="!p-3" tone={appErrorNoticeTone(appError)}
        title={t(scannerUnavailable ? "importWorkspace.error.uploadTitle" : "importWorkspace.error.title")}
        description={scannerUnavailable ? t("importWorkspace.error.scanUnavailable") : message || t(appError.messageKey)}
        dismiss={<button type="button" className="platforma-notice-close" aria-label={t("common.close")}
          onClick={() => { restoreNoticeFocus(card.current, opener.current); setDismissed(error); }}><X aria-hidden="true" size={16} /></button>}
        action={canShowSupportDetails(appError) || (!scannerUnavailable && action) ? <><RecoveryDetails error={appError} compact copyLabel={t("importWorkspace.error.copyCode")} />{scannerUnavailable ? null : action}</> : undefined}
      />
    </div> : null}
  </NotificationPresence></NotificationPortal>;
}
