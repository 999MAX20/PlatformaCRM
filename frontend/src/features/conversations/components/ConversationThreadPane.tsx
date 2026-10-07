import type { ReactNode, Ref } from "react";
import { useI18n } from "../../../lib/i18n";
import { useActiveBusiness } from "../../../hooks/useBusiness";
import {
  CheckCheck,
  MessageSquare,
  PauseCircle,
  PlayCircle,
  UserCheck,
} from "lucide-react";

import type { InboxConversation, InboxMessage } from "../../../api/inbox";
import { WorkQueueDetailPane } from "../../../components/layout/WorkQueueLayout";
import { Button } from "../../../components/ui/Button";
import { EmptyState, LoadingState } from "../../../components/ui/StateViews";
import type { Translate } from "../conversationTypes";
import { channelLabel, conversationTitle } from "../conversationUtils";
import { ConversationComposer } from "./ConversationComposer";
import { Pill, Tooltip } from "./ConversationPrimitives";
import { MessageBubble } from "./MessageBubble";
import { InboxMemoryControl } from "./InboxMemoryControl";

type ConversationThreadPaneProps = {
  selected: InboxConversation | null;
  mobileThreadOpen: boolean;
  mobileActions?: ReactNode;
  onMobileClose: () => void;
  messageScrollRef: Ref<HTMLDivElement>;
  messageEndRef: Ref<HTMLDivElement>;
  messagesLoading: boolean;
  messageList: InboxMessage[];
  canLoadMoreMessages: boolean;
  isFetchingNextPage: boolean;
  onLoadMoreMessages: () => void;
  draft: string;
  composerRef: Ref<HTMLTextAreaElement>;
  sendPending: boolean;
  onDraftChange: (value: string) => void;
  onResizeComposer: () => void;
  onOpenQuickReplies: () => void;
  onSendReply: () => void;
  onAssign: () => void;
  assignPending: boolean;
  onToggleBot: () => void;
  toggleBotPending: boolean;
  canToggleBot: boolean;
  onCloseConversation: () => void;
  closePending: boolean;
  onReopenConversation: () => void;
  reopenPending: boolean;
  t: Translate;
};

export function ConversationThreadPane({
  selected,
  mobileThreadOpen,
  mobileActions,
  onMobileClose,
  messageScrollRef,
  messageEndRef,
  messagesLoading,
  messageList,
  canLoadMoreMessages,
  isFetchingNextPage,
  onLoadMoreMessages,
  draft,
  composerRef,
  sendPending,
  onDraftChange,
  onResizeComposer,
  onOpenQuickReplies,
  onSendReply,
  onAssign,
  assignPending,
  onToggleBot,
  toggleBotPending,
  canToggleBot,
  onCloseConversation,
  closePending,
  onReopenConversation,
  reopenPending,
  t,
}: ConversationThreadPaneProps) {
  const { language } = useI18n();
  const { business } = useActiveBusiness();
  const availableAt = selected?.ai_safety?.next_call_available_at;
  const availableLabel = availableAt ? new Intl.DateTimeFormat(language, {
    dateStyle: "short", timeStyle: "short", timeZone: business?.timezone || "UTC",
  }).format(new Date(availableAt)) : "";
  return (
    <WorkQueueDetailPane
      className="min-w-0"
      mobileDetailOpen={mobileThreadOpen}
      closeLabel={t("common.close")}
      onMobileClose={onMobileClose}
    >
      {!selected ? (
        <div className="grid flex-1 place-items-center p-8">
          <div className="text-center">
            <div className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-card bg-platforma-card text-brand-600 shadow-xs">
              <MessageSquare aria-hidden="true" size={26} />
            </div>
            <p className="text-2xl font-bold text-platforma-muted">
              {t("conversations.selectDialog")}
            </p>
          </div>
        </div>
      ) : (
        <>
          {mobileActions ? <div className="flex flex-wrap gap-2 border-b border-platforma-border p-3 xl:hidden">{mobileActions}</div> : null}
          <div className="border-b border-platforma-border bg-platforma-card px-4 py-3">
            <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h2 className="truncate text-lg font-bold text-platforma-text">
                    {conversationTitle(selected, t)}
                  </h2>
                </div>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  <Pill className="bg-brand-50 text-brand-700 ring-brand-100">
                    {channelLabel(selected.channel, t)}
                  </Pill>
                  {selected.bot_enabled ? (
                    <Pill className="bg-[var(--platforma-success-soft)] text-platforma-success ring-platforma-success/20">
                      {t("conversations.botActive")}
                    </Pill>
                  ) : (
                    <Pill className="bg-surface-muted text-platforma-muted ring-platforma-border">
                      {t("conversations.botPaused")}
                    </Pill>
                  )}
                  {selected.handoff_required ? (
                    <Pill className="bg-[var(--platforma-warning-soft)] text-platforma-warning ring-platforma-warning/20">
                      {t("conversations.needsOperator")}
                    </Pill>
                  ) : null}
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <InboxMemoryControl key={selected.id} conversation={selected} />
                <Tooltip label={t("conversations.assignTooltip")}>
                  <Button
                    data-conversation-action-id="assign"
                    className="h-9 rounded-control px-3 text-xs"
                    variant="secondary"
                    disabled={!selected}
                    onClick={onAssign}
                    isLoading={assignPending}
                    aria-label={t("conversations.takeDialog")}
                  >
                    <UserCheck size={16} /> {t("conversations.takeDialog")}
                  </Button>
                </Tooltip>
                <Tooltip
                  label={
                    selected.bot_enabled
                      ? t("conversations.pauseBotTooltip")
                      : t("conversations.enableBotTooltip")
                  }
                >
                  <Button
                    data-conversation-action-id="toggle-bot"
                    className="h-9 rounded-control px-3 text-xs"
                    variant={selected.bot_enabled ? "warning" : "secondary"}
                    disabled={!canToggleBot || selected.status !== "open" || (!selected.bot_enabled && selected.ai_safety?.calls_remaining === 0)}
                    onClick={onToggleBot}
                    isLoading={toggleBotPending}
                    aria-label={
                      selected.bot_enabled
                        ? t("conversations.pauseBot")
                        : t("conversations.enableBot")
                    }
                  >
                    {selected.bot_enabled ? (
                      <PauseCircle size={16} />
                    ) : (
                      <PlayCircle size={16} />
                    )}
                    {selected.bot_enabled
                      ? t("conversations.pauseBot")
                      : t("conversations.enableBot")}
                  </Button>
                </Tooltip>
                {selected.status === "closed" ? (
                  <Tooltip label={t("conversations.reopenTooltip")}>
                    <Button
                      data-conversation-action-id="reopen"
                      className="h-9 rounded-control px-3 text-xs"
                      variant="secondary"
                      onClick={onReopenConversation}
                      isLoading={reopenPending}
                      aria-label={t("conversations.openDialog")}
                    >
                      <PlayCircle size={16} /> {t("common.open")}
                    </Button>
                  </Tooltip>
                ) : (
                  <Tooltip label={t("conversations.closeTooltip")}>
                    <Button
                      data-conversation-action-id="close"
                      className="h-9 rounded-control px-3 text-xs"
                      variant="secondary"
                      onClick={onCloseConversation}
                      isLoading={closePending}
                      aria-label={t("conversations.closeDialog")}
                    >
                      <CheckCheck size={16} /> {t("common.close")}
                    </Button>
                  </Tooltip>
                )}
              </div>
            </div>
            {selected.ai_safety && <div className="mt-2 space-y-1 text-xs text-platforma-subtle">
              <p>{t("customerSafety.usage", { used: selected.ai_safety.calls_used, limit: selected.ai_safety.calls_limit })}</p>
              {availableLabel && <p>{t("customerSafety.availableAt", { time: availableLabel })}</p>}
              {selected.handoff_required && selected.handoff_reason && <p role="status">{selected.handoff_reason}</p>}
              {!selected.bot_enabled && selected.ai_safety.reason && <p>{t("customerSafety.resumeHint")}</p>}
            </div>}
          </div>

          <div
            ref={messageScrollRef}
            className="min-h-0 flex-1 space-y-4 overflow-y-auto bg-surface-warm p-5 pb-28 lg:pb-5"
          >
            {messagesLoading ? (
              <LoadingState />
            ) : null}
            {canLoadMoreMessages ? (
              <Button
                type="button"
                className="h-8 min-h-8 rounded-control px-3 text-xs"
                variant="secondary"
                onClick={onLoadMoreMessages}
                isLoading={isFetchingNextPage}
              >
                {t("conversations.loadEarlier")}
              </Button>
            ) : null}
            {!messagesLoading && !messageList.length ? (
              <EmptyState
                title={t("conversations.noMessagesTitle")}
                description={t("conversations.noMessagesText")}
              />
            ) : null}
            {messageList.length ? (
              <div className="sticky top-0 z-10 flex justify-center">
                <span className="rounded-full bg-platforma-card/90 px-3 py-1 text-xs font-bold text-platforma-muted shadow-xs ring-1 ring-platforma-border">
                  {t("common.today")}
                </span>
              </div>
            ) : null}
            {messageList.map((message) => (
              <MessageBubble key={message.id} message={message} t={t} />
            ))}
            <div ref={messageEndRef} aria-hidden="true" />
          </div>

          <ConversationComposer
            selected={selected}
            draft={draft}
            composerRef={composerRef}
            sendPending={sendPending}
            onDraftChange={onDraftChange}
            onResizeComposer={onResizeComposer}
            onOpenQuickReplies={onOpenQuickReplies}
            onSendReply={onSendReply}
            t={t}
          />
        </>
      )}
    </WorkQueueDetailPane>
  );
}
