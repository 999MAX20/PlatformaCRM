import type { InboxClientLinkPreview } from "../../../api/inbox";
import { Button } from "../../../components/ui/Button";
import { ErrorState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";

type Props = {
  preview: InboxClientLinkPreview;
  refreshed: boolean;
  pending: boolean;
  error: unknown;
  onCancel: () => void;
  onConfirm: () => void;
};

export function ClientLinkConfirmation({ preview, refreshed, pending, error, onCancel, onConfirm }: Props) {
  const { t } = useI18n();
  return <div className="space-y-4 p-4">
    <p className="break-words font-semibold text-platforma-ink">
      {preview.previous_client?.title || t("conversations.clientReplacement.previousHidden")}
      {" → "}{preview.next_client.title}
    </p>
    {refreshed ? <p role="status" className="text-sm text-platforma-muted">{t("conversations.clientReplacement.refreshed")}</p> : null}
    {preview.conflicts.length ? <>
      <p className="text-sm text-platforma-muted">{t("conversations.clientReplacement.conflicts")}</p>
      <ul className="space-y-2 text-sm">
        {preview.conflicts.map(({ kind, entity }) => <li key={kind} className="break-words rounded-lg border border-platforma-border p-3">
          <span className="font-semibold">{t(`conversations.clientReplacement.${kind}`)}</span>
          {entity ? <> #{entity.id}{entity.title ? ` — ${entity.title}` : ""}</> : <> — {t("conversations.clientReplacement.hidden")}</>}
        </li>)}
      </ul>
    </> : null}
    <p className="text-sm text-platforma-muted">{t("conversations.clientReplacement.preserved")}</p>
    {error ? <ErrorState error={error} /> : null}
    <div className="flex flex-wrap justify-end gap-2">
      <Button variant="secondary" disabled={pending} onClick={onCancel} autoFocus>{t("common.cancel")}</Button>
      <Button isLoading={pending} onClick={onConfirm}>{t("conversations.clientReplacement.confirm")}</Button>
    </div>
  </div>;
}
