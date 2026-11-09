import type { AppError } from "../../api/appError";

type NotificationIdentity = {
  appError?: AppError;
  dedupeKey?: string;
  message?: string;
  title?: string;
  description?: string;
  tone?: string;
  onAction?: unknown;
};

export function notificationDedupeKey(item: NotificationIdentity) {
  if (item.dedupeKey) return `event:${item.dedupeKey}`;
  if (item.appError?.requestId) return `request:${item.appError.requestId}:${item.appError.code}`;
  // Equal generic text does not prove that two actionable operations are equal.
  if (item.onAction || !(item.message || item.title || item.description)) return undefined;
  return `notice:${JSON.stringify([item.tone || (item.appError ? "danger" : "info"), item.title, item.description, item.message, item.appError?.messageKey])}`;
}

export function notificationContent(item: NotificationIdentity, fallback: string) {
  const title = item.title || item.message || fallback;
  const description = item.description || (item.title ? item.message || (item.appError ? fallback : undefined) : undefined);
  return { title, description: description && description !== title ? description : undefined };
}
