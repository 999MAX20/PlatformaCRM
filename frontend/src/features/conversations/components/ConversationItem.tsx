import { CheckSquare, MessageSquare, Square } from "lucide-react";

import type { InboxConversation } from "../../../api/inbox";
import { cn } from "../../../lib/cn";
import type { Translate } from "../conversationTypes";
import { channelLabel, conversationTitle, formatDateTime } from "../conversationUtils";

export function ConversationItem({
  conversation,
  active,
  selectable,
  selectedForBulk,
  onToggleSelected,
  onClick,
  t,
}: {
  conversation: InboxConversation;
  active: boolean;
  selectable: boolean;
  selectedForBulk: boolean;
  onToggleSelected: () => void;
  onClick: () => void;
  t: Translate;
}) {
  const preview = conversation.last_message?.text || t("conversations.emptyHistoryPreview");
  const unread = conversation.unread_count || 0;
  const isSlaOverdue = Boolean(conversation.sla_overdue || (conversation.sla_overdue_minutes || 0) > 0);
  const initials = conversationTitle(conversation, t)
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div
      role="button"
      aria-current={active ? "true" : undefined}
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(event) => {
        if (event.target === event.currentTarget && (event.key === "Enter" || event.key === " ")) {
          event.preventDefault();
          onClick();
        }
      }}
      className={cn(
        "platforma-focus-ring group relative w-full border-b border-platforma-border px-3 py-1 text-left transition hover:bg-surface-hover",
        active ? "bg-brand-50/80 before:absolute before:bottom-0 before:left-0 before:top-0 before:w-1 before:bg-[var(--platforma-brand-content)]" : "bg-platforma-card",
      )}
    >
      <div className="flex items-center gap-2.5">
        {selectable ? (
          <button
            type="button"
            className="grid h-11 w-11 shrink-0 place-items-center rounded-control text-platforma-muted hover:bg-platforma-card lg:h-9 lg:w-9"
            onClick={(event) => {
              event.stopPropagation();
              onToggleSelected();
            }}
            aria-label={selectedForBulk ? t("conversations.removeFromSelection") : t("conversations.selectForBulk")}
          >
            {selectedForBulk ? <CheckSquare size={19} /> : <Square size={19} />}
          </button>
        ) : null}
        <div aria-hidden="true" className="relative grid h-8 w-8 shrink-0 place-items-center rounded-full border border-platforma-border bg-platforma-card text-xs font-bold text-brand-700">
          {initials || <MessageSquare size={16} />}
        </div>
        <div className="min-w-0 flex-1 text-left">
          <div className="flex items-center gap-2">
            <p title={conversationTitle(conversation, t)} className="min-w-0 flex-1 truncate text-sm font-semibold leading-5 text-platforma-text">{conversationTitle(conversation, t)}</p>
            <span className="shrink-0 text-[11px] text-platforma-muted">{formatDateTime(conversation.last_message_at)}</span>
          </div>
          <div className="flex items-center gap-2"><p className="min-w-0 flex-1 truncate text-xs leading-4 text-platforma-muted">{preview}</p>
            {unread > 0 ? <span className="grid h-4 min-w-4 shrink-0 place-items-center rounded-full bg-brand-500 px-1 text-[10px] font-bold text-white">{unread}</span> : null}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-1.5 leading-4">
            <span className="text-[11px] text-platforma-muted">{channelLabel(conversation.channel, t)}</span>
            {conversation.handoff_required ? <span className="rounded-full bg-[var(--platforma-danger-soft)] px-1.5 py-0.5 text-[10px] font-bold text-platforma-danger">{t("conversations.noReply")}</span> : null}
            {isSlaOverdue ? <span className="rounded-full bg-[var(--platforma-danger-soft)] px-1.5 py-0.5 text-[10px] font-bold text-platforma-danger">{t("conversations.slaOverdue")}</span> : null}
            {!conversation.handoff_required && !conversation.bot_enabled ? <span className="rounded-full bg-[var(--platforma-warning-soft)] px-1.5 py-0.5 text-[10px] font-bold text-platforma-warning">{t("conversations.paused")}</span> : null}
            {conversation.status === "closed" ? <span className="rounded-full bg-surface-muted px-1.5 py-0.5 text-[10px] font-bold text-platforma-muted">{t("status.closed")}</span> : null}
          </div>
        </div>
      </div>
    </div>
  );
}
