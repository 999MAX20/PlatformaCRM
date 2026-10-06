import type { AppError } from "../../api/appError";

type NotificationIdentity = {
  appError?: AppError;
  dedupeKey?: string;
  message?: string;
  tone?: string;
  onAction?: unknown;
};

export function notificationDedupeKey(item: NotificationIdentity) {
  if (item.dedupeKey) return `event:${item.dedupeKey}`;
  if (item.appError?.requestId) return `request:${item.appError.requestId}:${item.appError.code}`;
  // Equal generic text does not prove that two actionable operations are equal.
  if (item.onAction || !item.message) return undefined;
  return `notice:${item.tone || "info"}:${item.message}`;
}
