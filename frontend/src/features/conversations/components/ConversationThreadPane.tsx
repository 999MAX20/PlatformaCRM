import type { ReactNode, Ref } from "react";
import { useI18n } from "../../../lib/i18n";
import { useActiveBusiness } from "../../../hooks/useBusiness";
import { dateInTimeZone } from "../../../lib/format";
import { MessageSquare } from "lucide-react";

import type { InboxConversation, InboxMessage } from "../../../api/inbox";
import { WorkQueueDetailPane } from "../../../components/layout/WorkQueueLayout";
import { Button } from "../../../components/ui/Button";
import { EmptyState, LoadingState } from "../../../components/ui/StateViews";
import type { Translate } from "../conversationTypes";
import type { ActionMenuItem } from "../../../components/ui/ActionMenu";
import { ConversationThreadHeader } from "./ConversationThreadHeader";
import { ConversationComposer } from "./ConversationComposer";
import { MessageBubble } from "./MessageBubble";

type ConversationThreadPaneProps = {
  selected: InboxConversation | null;
  connectChannelAction?: ReactNode;
  mobileThreadOpen: boolean;
  threadMenu: ActionMenuItem[];
  headerActions?: ReactNode;
  aiActions?: ReactNode;
  aiPreview?: ReactNode;
  canUpdate: boolean;
  renderDelivery: (message: InboxMessage) => ReactNode;
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
  connectChannelAction,
  mobileThreadOpen,
  threadMenu,
  headerActions,
  aiActions,
  aiPreview,
  canUpdate,
  renderDelivery,
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
  const messageDay = (message: InboxMessage) => dateInTimeZone(message.created_at, business?.timezone || "UTC");
  const today = dateInTimeZone(new Date(), business?.timezone || "UTC");
  const availableAt = selected?.ai_safety?.next_call_available_at;
  const availableLabel = availableAt ? new Intl.DateTimeFormat(language, {
    dateStyle: "short", timeStyle: "short", timeZone: business?.timezone || "UTC",
  }).format(new Date(availableAt)) : "";
  const resumeLabel = selected?.ai_resume_at ? new Intl.DateTimeFormat(language, {
    dateStyle: "short", timeStyle: "short", timeZone: business?.timezone || "UTC",
  }).format(new Date(selected.ai_resume_at)) : "";
  return (
    <WorkQueueDetailPane
      className="min-w-0"
      mobileDetailOpen={mobileThreadOpen}
    >
      {!selected ? (
        <div className="grid flex-1 place-items-center p-8">
          <div className="relative text-center">
            <div className="absolute inset-x-0 bottom-full mb-4 flex justify-center text-brand-600">
              <MessageSquare aria-hidden="true" size={26} />
            </div>
            {connectChannelAction || <p className="text-2xl font-bold text-platforma-muted">
              {t("conversations.selectDialog")}
            </p>}
          </div>
        </div>
      ) : (
        <>
          <ConversationThreadHeader selected={selected} headerActions={headerActions} threadMenu={threadMenu} canUpdate={canUpdate} canToggleBot={canToggleBot} onMobileClose={onMobileClose} onAssign={onAssign} assignPending={assignPending} onToggleBot={onToggleBot} toggleBotPending={toggleBotPending} onCloseConversation={onCloseConversation} closePending={closePending} onReopenConversation={onReopenConversation} reopenPending={reopenPending} t={t} />
          {selected.status === "open" && selected.handoff_required && !selected.bot_enabled && selected.handoff_resume_started_at && (
            <p role="status" data-testid="inbox-ai-return" className="shrink-0 border-b border-platforma-border bg-platforma-card px-4 py-2 text-xs text-platforma-subtle">
              {resumeLabel ? t("conversations.aiReturnsAfter", { time: resumeLabel }) : t("conversations.aiReturnWaiting")}
            </p>
          )}
            {selected.ai_safety && (availableLabel || (selected.handoff_required && selected.handoff_reason) || (!selected.bot_enabled && selected.ai_safety.reason)) && <div className="shrink-0 space-y-1 border-b border-platforma-border bg-platforma-card px-4 py-2 text-xs text-platforma-subtle">
              {availableLabel && <p>{t("customerSafety.availableAt", { time: availableLabel })}</p>}
              {selected.handoff_required && selected.handoff_reason && <p role="status">{selected.handoff_reason}</p>}
              {!selected.bot_enabled && selected.ai_safety.reason && <p>{t("customerSafety.resumeHint")}</p>}
            </div>}

          <div
            ref={messageScrollRef}
            className="min-h-0 flex-1 space-y-3 overflow-x-hidden overflow-y-auto overscroll-contain bg-surface-warm p-4"
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
            {messageList.map((message, index) => (
              <div key={message.id} data-message-id={message.id}>
                {index === 0 || messageDay(message) !== messageDay(messageList[index - 1]) ? (
                  <div className="mb-3 flex justify-center" data-testid="inbox-message-date">
                    <span className="rounded-full bg-platforma-card/90 px-3 py-1 text-xs font-bold text-platforma-muted shadow-xs ring-1 ring-platforma-border">
                      {messageDay(message) === today ? t("common.today") : new Intl.DateTimeFormat(language, {
                        day: "numeric", month: "short", year: "numeric", timeZone: business?.timezone || "UTC",
                      }).format(new Date(message.created_at))}
                    </span>
                  </div>
                ) : null}
                <MessageBubble message={message} t={t} language={language} timeZone={business?.timezone || "UTC"} />
                {message.direction === "outbound" && message.sender_type !== "system" ? renderDelivery(message) : null}
              </div>
            ))}
            <div ref={messageEndRef} aria-hidden="true" />
          </div>

          <ConversationComposer
            selected={selected}
            draft={draft}
            composerRef={composerRef}
            sendPending={sendPending}
            canReply={canUpdate}
            aiActions={aiActions}
            aiPreview={aiPreview}
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
