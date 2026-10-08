import type { ReactNode, Ref } from "react";
import { Tags } from "lucide-react";

import type { InboxConversation } from "../../../api/inbox";
import { Button } from "../../../components/ui/Button";
import { StatusNotice } from "../../../components/ui/StatusNotice";
import type { Translate } from "../conversationTypes";

type ConversationComposerProps = {
  selected: InboxConversation;
  draft: string;
  composerRef: Ref<HTMLTextAreaElement>;
  sendPending: boolean;
  canReply: boolean;
  aiActions?: ReactNode;
  onDraftChange: (value: string) => void;
  onResizeComposer: () => void;
  onOpenQuickReplies: () => void;
  onSendReply: () => void;
  t: Translate;
};

export function ConversationComposer({
  selected,
  draft,
  composerRef,
  sendPending,
  canReply,
  aiActions,
  onDraftChange,
  onResizeComposer,
  onOpenQuickReplies,
  onSendReply,
  t,
}: ConversationComposerProps) {
  return (
    <div className="border-t border-platforma-border bg-platforma-card p-3">
      {selected.status === "closed" ? (
        <StatusNotice
          compact
          className="mb-3"
          tone="warning"
          title={t("conversations.closedReplyNotice")}
        />
      ) : null}
      <div className="mb-2 flex flex-wrap items-center gap-2">
        {aiActions}
        <Button variant="ghost" size="sm" disabled={!canReply || selected.status === "closed"} onClick={onOpenQuickReplies}>
          <Tags size={15} /> {t("conversations.quickRepliesButton")}
        </Button>
      </div>
      <div className="flex items-end gap-2 rounded-card border border-platforma-border bg-platforma-card px-3 py-2 shadow-xs">
        <textarea
          data-testid="inbox-action-composer"
          ref={composerRef}
          rows={1}
          className="platforma-focus-ring max-h-28 min-h-10 min-w-0 flex-1 resize-none bg-transparent py-2 text-sm text-platforma-text outline-hidden placeholder:text-platforma-muted disabled:bg-disabled-surface disabled:text-disabled-content disabled:placeholder:text-disabled-content disabled:opacity-100"
          disabled={!canReply || selected.status === "closed" || sendPending}
          placeholder={t("conversations.replyPlaceholder")}
          value={draft}
          onChange={(event) => {
            onDraftChange(event.target.value);
            window.requestAnimationFrame(onResizeComposer);
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) onSendReply();
          }}
        />
        <Button
          data-testid="inbox-action-send"
          variant="primary"
          className="h-10 shrink-0 rounded-control px-4 text-sm"
          disabled={!canReply || selected.status === "closed" || !draft.trim()}
          isLoading={sendPending}
          onClick={onSendReply}
          title={t("conversations.send")}
        >
          {t("conversations.send")}
        </Button>
      </div>
    </div>
  );
}
