import { useEffect, useState } from "react";
import { Button } from "../../../components/ui/Button";
import { Modal } from "../../../components/ui/Modal";
import { useActionConfirm } from "../../../components/actions/ActionConfirmProvider";
import { useI18n } from "../../../lib/i18n";
import { retryBlockedReason } from "../../../lib/leadOfflineCommands";
import type { OfflineLeadAction } from "../types";

export function LeadOfflineQueueStatus({ queue, storageError, syncing, online, recover }: {
  queue: OfflineLeadAction[]; storageError: string; syncing: boolean; online: boolean;
  recover: (id: string, discard?: boolean) => Promise<void>;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const confirm = useActionConfirm();
  useEffect(() => { if (!queue.length) setOpen(false); }, [queue.length]);
  if (!queue.length && !storageError) return null;
  return <div className="shrink-0 space-y-2" data-testid="lead-offline-queue">
    {storageError && <p role="alert" className="text-sm text-platforma-danger">{t(storageError)}</p>}
    <Button variant="secondary" onClick={() => setOpen(true)}>{t("leads.offlinePending", { count: queue.length })}</Button>
    <Modal open={open} onClose={() => setOpen(false)} title={t("leads.offlineQueueTitle")} size="lg">
      <div className="space-y-3">
        {!queue.length && <p>{t("leads.queueEmpty")}</p>}
        {queue.map(item => <article key={item.id} className="rounded-xl border border-platforma-border p-3 space-y-2">
          <p className="font-semibold">{t(item.type === "note" ? "crmCard.note" : "crmCard.createTask")} · {t("crmCard.leadNumber", { id: item.leadId })}</p>
          <p className="whitespace-pre-wrap break-words text-sm">{item.type === "note" ? item.text : item.title}</p>
          {item.type === "task" && item.due_at && <p className="text-sm">{item.due_at}</p>}
          <p role={item.errorKey ? "alert" : "status"} className="text-sm">{t(retryBlockedReason(item) || item.errorKey || "leads.queueWaiting")}</p>
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" disabled={!online || syncing || Boolean(retryBlockedReason(item))} onClick={() => void recover(item.id)}>{t("common.retry")}</Button>
            <Button variant="secondary" disabled={syncing} onClick={async () => {
              const result = await confirm({ title: t("leads.queueDiscard"), description: t("leads.queueDiscardConfirm"), confirmLabel: t("leads.queueDiscard"), tone: "danger" });
              if (result.confirmed) await recover(item.id, true);
            }}>{t("leads.queueDiscard")}</Button>
          </div>
        </article>)}
      </div>
    </Modal>
  </div>;
}
