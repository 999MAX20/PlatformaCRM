import { formatDateTime } from "../../../lib/format";
import { useI18n } from "../../../lib/i18n";
import type { CrmCardPayload } from "../../../types";
import { StatusBadge } from "../../ui/StatusBadge";
import { drawerSurfaceClass, EmptyBlock, getChannelLabel } from "./shared";

export function EntityConversationsPanel({ data }: { data: CrmCardPayload }) {
  const { t } = useI18n();
  return (
    <div className="space-y-3">
      {data.conversations.map((conversation) => (
        <div key={conversation.id} className={drawerSurfaceClass}>
          <div className="flex items-center justify-between gap-3">
            <p className="font-bold text-platforma-ink">{getChannelLabel(conversation.channel, t)}</p>
            <StatusBadge status={conversation.status} />
          </div>
          <p className="mt-1 text-xs text-platforma-muted">{t("crmCard.unread")}: {conversation.unread_count || 0} · {formatDateTime(conversation.last_message_at || conversation.updated_at)}</p>
          {conversation.last_message?.text ? <p className="mt-3 text-sm leading-6 text-platforma-subtle">{conversation.last_message.text}</p> : null}
        </div>
      ))}
      {!data.conversations.length ? <EmptyBlock title={t("crmCard.noDialogs")} text={t("crmCard.noDialogsText")} /> : null}
    </div>
  );
}
