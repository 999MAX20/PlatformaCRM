import { Paperclip, Sparkles } from "lucide-react";

import type { InboxMessage } from "../../../api/inbox";
import { cn } from "../../../lib/cn";
import type { Translate } from "../conversationTypes";
import { formatMessageTime } from "../conversationUtils";
import { AttachmentScanStatus } from "../../../components/crm/AttachmentScanStatus";

export function MessageBubble({ message, t, language, timeZone }: { message: InboxMessage; t: Translate; language: string; timeZone: string }) {
  const system = message.sender_type === "system";
  const inbound = message.direction === "inbound";
  const ai = message.sender_type === "bot" || message.sender_type === "ai";
  const author = ai
    ? t("conversations.senderAssistant")
    : message.sender_type === "manager"
      ? t("conversations.senderManager")
      : t("conversations.senderClient");
  const time = formatMessageTime(message.created_at || message.sent_at, language, timeZone);

  if (system) {
    return (
      <div className="flex justify-center">
        <div className="max-w-[80%] rounded-full bg-surface-muted px-3 py-1.5 text-center text-xs font-bold text-platforma-muted">
          {message.text || t("conversations.emptyMessage")}
          {time ? <span className="ml-2 text-platforma-muted">{time}</span> : null}
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn("flex", inbound ? "justify-start" : "justify-end")}
      data-testid="conversation-message"
      data-message-direction={message.direction}
      data-message-sender={message.sender_type}
      data-message-status={message.status}
    >
      <div
        className={cn(
          "max-w-[min(85%,720px)] rounded-card border border-platforma-border bg-platforma-card px-3 py-2 text-sm font-medium leading-[22px] text-platforma-text shadow-xs",
          inbound ? "rounded-tl-md" : "rounded-tr-md",
        )}
        data-testid="conversation-message-bubble"
      >
        <p className="whitespace-pre-wrap [overflow-wrap:anywhere]">
          {message.text || t("conversations.emptyMessage")}
        </p>
        {message.attachments?.length ? (
          <div className="mt-3 space-y-2 text-platforma-text">
            {message.attachments.map((attachment) => (
              <div key={attachment.id}>
                <a
                  href={attachment.scan_status === "clean" ? attachment.download_url : undefined}
                  aria-disabled={attachment.scan_status !== "clean"}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-2 rounded-control bg-surface-muted px-3 py-2 text-xs font-bold ring-1 ring-platforma-border"
                >
                  <Paperclip size={14} />
                  <span className="min-w-0 flex-1 truncate">
                    {attachment.original_name}
                  </span>
                </a>
                <AttachmentScanStatus attachment={attachment} />
              </div>
            ))}
          </div>
        ) : null}
        <div className="mt-1 flex flex-wrap items-center justify-end gap-2 text-xs leading-4 text-platforma-subtle">
          <span className="inline-flex items-center gap-1">{ai ? <Sparkles size={12} /> : null}{author}</span>
          {time ? <span className="tabular-nums">{time}</span> : null}
        </div>
      </div>
    </div>
  );
}
