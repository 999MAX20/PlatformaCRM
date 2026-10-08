import { AlertTriangle, CheckCircle2, Clock3, LoaderCircle, RefreshCw, Send } from "lucide-react";

import type { InboxMessage } from "../../../api/inbox";
import { Button } from "../../../components/ui/Button";
import type { Translate } from "../conversationTypes";
import { Pill } from "./ConversationPrimitives";

export type DeliveryStatus = "queued" | "sending" | "delivered" | "delayed" | "retrying" | "failed";

export function getDeliveryStatus(message: InboxMessage): DeliveryStatus {
  if (message.status === "delivering") return "sending";
  if (message.status === "retry_scheduled") {
    return message.delivery_next_retry_at ? "delayed" : "retrying";
  }
  if (message.status === "sent") return "delivered";
  if (message.status === "failed") return "failed";
  return "queued";
}

const statusCopy: Record<DeliveryStatus, string> = {
  queued: "conversations.deliveryStatusQueued",
  sending: "conversations.deliveryStatusSending",
  delivered: "conversations.deliveryStatusDelivered",
  delayed: "conversations.deliveryStatusDelayed",
  retrying: "conversations.deliveryStatusRetrying",
  failed: "conversations.deliveryStatusFailed",
};

const statusHelp: Record<DeliveryStatus, string> = {
  queued: "conversations.deliveryHelpQueued",
  sending: "conversations.deliveryHelpSending",
  delivered: "conversations.deliveryHelpDelivered",
  delayed: "conversations.deliveryHelpDelayed",
  retrying: "conversations.deliveryHelpRetrying",
  failed: "conversations.deliveryHelpFailed",
};

function statusIcon(status: DeliveryStatus) {
  if (status === "sending" || status === "retrying") return LoaderCircle;
  if (status === "delivered") return CheckCircle2;
  if (status === "delayed") return Clock3;
  if (status === "failed") return AlertTriangle;
  if (status === "queued") return Send;
  return RefreshCw;
}

function statusClass(status: DeliveryStatus) {
  if (status === "delivered") return "bg-[var(--platforma-success-soft)] text-platforma-text ring-platforma-success/[0.18]";
  if (status === "failed") return "bg-[var(--platforma-danger-soft)] text-platforma-danger ring-platforma-danger/[0.18]";
  if (status === "delayed" || status === "retrying") return "bg-platforma-warning-soft text-platforma-text ring-platforma-warning/[0.22]";
  return "bg-surface-muted text-platforma-muted ring-platforma-border";
}

export function MessageDeliveryDetails({
  message,
  canRetry,
  retryPending,
  onRetry,
  t,
}: {
  message: InboxMessage;
  canRetry: boolean;
  retryPending: boolean;
  onRetry: () => void;
  t: Translate;
}) {
  const status = getDeliveryStatus(message);
  const Icon = statusIcon(status);
  const attempts = message.delivery_attempts || 0;
  const maxAttempts = message.delivery_max_attempts || attempts;

  return (
    <section
      data-testid="message-delivery-details"
      className="ml-auto mt-1 max-w-[78%] px-1 text-right"
    >
      <div className="flex flex-wrap items-center justify-end gap-2">
        <p className="flex items-center gap-1 text-xs text-platforma-muted">
          <Icon aria-hidden="true" className={status === "sending" || status === "retrying" ? "animate-spin motion-reduce:animate-none" : ""} size={15} />
        </p>
        <Pill className={statusClass(status)}>{t(statusCopy[status])}</Pill>
      {attempts > 0 && status !== "delivered" ? (
        <p className="text-[11px] text-platforma-muted">
          {t("conversations.deliveryAttempts", { attempts, max: maxAttempts })}
        </p>
      ) : null}
      {status === "failed" && canRetry ? (
        <Button
          type="button"
          data-testid="message-delivery-retry"
          className="min-h-11 px-2 text-xs lg:min-h-9"
          size="sm"
          variant="ghost"
          onClick={onRetry}
          isLoading={retryPending}
        >
          <RefreshCw size={14} /> {t("conversations.retryDelivery")}
        </Button>
      ) : null}
      </div>
      {status !== "delivered" ? <p className="mt-1 text-xs text-platforma-muted">{t(statusHelp[status])}</p> : null}
      {status === "failed" && !canRetry ? (
        <p className="mt-3 text-xs font-semibold text-platforma-muted">
          {t("conversations.deliveryRetryNotAllowed")}
        </p>
      ) : null}
    </section>
  );
}
