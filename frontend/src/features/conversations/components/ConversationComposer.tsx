import type { ReactNode, Ref } from "react";
import { Tags } from "lucide-react";

import type { InboxConversation } from "../../../api/inbox";
import { Button } from "../../../components/ui/Button";
import { Tooltip } from "./ConversationPrimitives";
import { StatusNotice } from "../../../components/ui/StatusNotice";
import type { Translate } from "../conversationTypes";

type ConversationComposerProps = {
  selected: InboxConversation;
  draft: string;
  composerRef: Ref<HTMLTextAreaElement>;
  sendPending: boolean;
  canReply: boolean;
  aiActions?: ReactNode;
  aiPreview?: ReactNode;
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
  aiPreview,
  onDraftChange,
  onResizeComposer,
  onOpenQuickReplies,
  onSendReply,
  t,
}: ConversationComposerProps) {
  return (
    <div data-testid="inbox-composer" className="shrink-0 border-t border-platforma-border bg-platforma-card px-3 py-[17px] lg:px-4">
      {selected.status === "closed" ? (
        <StatusNotice
          compact
          className="mb-3"
          tone="warning"
          title={t("conversations.closedReplyNotice")}
        />
      ) : null}
      {aiPreview}
      <div className="flex items-end gap-2">
        {aiActions}
        <Tooltip label={t("conversations.quickRepliesButton")} side="top"><Button variant="ghost" size="icon" className="h-11 w-11 shrink-0" data-focus-return-id="inbox-quick-replies" aria-label={t("conversations.quickRepliesButton")} disabled={!canReply || selected.status === "closed"} onClick={onOpenQuickReplies}>
          <Tags size={18} />
        </Button></Tooltip>
        <textarea
          data-testid="inbox-action-composer"
          aria-label={t("conversations.replyPlaceholder")}
          ref={composerRef}
          rows={1}
          className="platforma-focus-ring min-h-11 min-w-0 flex-1 resize-none rounded-control border border-platforma-control bg-platforma-card px-3 py-[10px] text-sm leading-[22px] text-platforma-text outline-hidden placeholder:text-platforma-muted disabled:bg-disabled-surface disabled:text-disabled-content disabled:placeholder:text-disabled-content disabled:opacity-100"
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
          className="h-11 shrink-0 rounded-control px-3 text-sm"
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
