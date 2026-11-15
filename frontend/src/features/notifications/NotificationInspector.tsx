import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { Link } from "react-router";

import { invalidateNotificationReceipts } from "../../lib/notificationCache";
import { notificationsApi } from "../../api/notifications";
import { normalizeAppError } from "../../api/appError";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useAuth } from "../auth/AuthProvider";
import { formatDateTime } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import { realtimeIntervals } from "../../lib/realtime";
import type { Id, Notification } from "../../types";

export function notificationText(notification: Notification, t: (key: string) => string) {
  return notification.message_key ? t(notification.message_key) : notification.text;
}

export function NotificationInspector({ id, business, onClose, inline = false }: { id: Id; business: Id; onClose: () => void; inline?: boolean }) {
  const { t, language } = useI18n();
  const { user } = useAuth();
  const panelRef = useRef<HTMLElement | null>(null);
  useEffect(() => { if (inline) panelRef.current?.focus(); }, [id, inline]);
  useEffect(() => {
    if (!inline) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || event.defaultPrevented || document.querySelector('[role="dialog"][aria-modal="true"], #notification-menu')) return;
      event.preventDefault();
      onClose();
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [inline, onClose]);
  const client = useQueryClient();
  const queryKey = ["notification-detail", business, user?.id, id];
  const detail = useQuery({ queryKey, queryFn: () => notificationsApi.personalDetail(id, business),
    refetchInterval: realtimeIntervals.notificationsMs, refetchOnWindowFocus: true, retry: false });
  const opened = useMutation({ mutationFn: () => notificationsApi.open(id, business), onSuccess: data => {
    client.setQueryData(queryKey, data); return invalidateNotificationReceipts(client);
  } });
  const attempted = useRef(false);
  useEffect(() => {
    if (detail.isSuccess && !detail.isError && !attempted.current) {
      attempted.current = true;
      opened.mutate();
    }
  }, [detail.isSuccess, detail.isError, opened.mutate]);
  const acknowledge = useMutation({ mutationFn: () => notificationsApi.acknowledge(id, business), onSuccess: data => {
    client.setQueryData(queryKey, data); return invalidateNotificationReceipts(client);
  } });
  const unread = useMutation({ mutationFn: () => notificationsApi.markUnread(id, business), onSuccess: data => {
    client.setQueryData(queryKey, data); return invalidateNotificationReceipts(client);
  } });
  const read = useMutation({ mutationFn: () => notificationsApi.markRead(id, business), onSuccess: data => {
    client.setQueryData(queryKey, data); return invalidateNotificationReceipts(client);
  } });
  const notification = detail.data;
  const mutationError = opened.error || acknowledge.error || unread.error || read.error;
  const accessLost = mutationError && ["permission", "not_found", "authentication"].includes(normalizeAppError(mutationError).category);
  const content = <>
    {accessLost ? <ErrorState error={mutationError} /> : detail.isPending ? <LoadingState /> : detail.isError ? <ErrorState error={detail.error}
      action={normalizeAppError(detail.error).retryable ? <Button variant="secondary" onClick={() => void detail.refetch()}>{t("common.retry")}</Button> : undefined} /> : notification ? <div className="space-y-4">
      <div className="space-y-2 border-b border-platforma-border pb-4">
        <h3 className={`break-words text-base font-semibold text-platforma-ink ${inline ? "pr-10" : ""}`}>{notification.message_key ? notificationText(notification, t) : t(notification.kind === "announcement" ? "notification.announcement" : "notification.workItem")}</h3>
        <p className="text-sm text-platforma-subtle">{formatDateTime(notification.send_at, undefined, false, language)}</p>
        <p className="text-sm text-platforma-subtle">{t(`notification.category.${notification.category === "ai_alerts" ? "aiAlerts" : notification.category}`)} · {notification.client_name || "CRM"}</p>
        <p className="text-xs text-platforma-subtle">{t("notification.priorityLabel")}: {t(`notification.priority.${notification.priority}`)}</p>
      </div>
      {!notification.message_key ? <p className="whitespace-pre-wrap break-words text-sm leading-6 text-platforma-ink">{notificationText(notification, t)}</p> : null}
      {notification.author_name ? <p className="text-xs text-platforma-subtle">{notification.author_name}</p> : null}
      {mutationError ? <ErrorState error={mutationError} /> : null}
      {opened.isError ? <Button variant="secondary" onClick={() => opened.mutate()}>{t("common.retry")}</Button> : null}
      {notification.acknowledged_at ? <p role="status" className="text-sm text-platforma-subtle">{t("notification.acknowledged")} · {formatDateTime(notification.acknowledged_at, undefined, false, language)}</p> : null}
      <div className="flex flex-wrap gap-2">
        {notification.kind === "announcement" && !notification.acknowledged_at ? <Button
          onClick={() => acknowledge.mutate()} disabled={!notification.opened_at || opened.isPending || acknowledge.isPending}
          isLoading={acknowledge.isPending}>{t("notification.acknowledge")}</Button> : null}
        {notification.action_url ? <Link to={notification.action_url} onClick={onClose}
          className="platforma-focus-ring inline-flex min-h-11 items-center rounded-control bg-brand-500 px-4 text-sm font-semibold text-white">{notification.action_label || t("common.open")}</Link> : null}
        {notification.read_at ? <Button variant="ghost" onClick={() => unread.mutate()} disabled={opened.isPending || unread.isPending || read.isPending} isLoading={unread.isPending}>{t("notification.markUnread")}</Button>
          : <Button variant="ghost" onClick={() => read.mutate()} disabled={opened.isPending || read.isPending || unread.isPending} isLoading={read.isPending}>{t("notification.markRead")}</Button>}
      </div>
    </div> : null}
  </>;
  return inline ? <aside ref={panelRef} tabIndex={-1}
    className="platforma-focus-ring relative min-w-0 border-l border-platforma-border p-5" aria-label={t("header.notifications")} data-testid="notification-inspector">
    <Button variant="ghost" size="icon" className="absolute right-2 top-2 h-11 w-11" aria-label={t("common.close")} onClick={onClose}><X size={20} aria-hidden="true" /></Button>
    {content}
  </aside> : <Modal title={t("header.notifications")} open onClose={onClose} testId="notification-inspector">{content}</Modal>;
}
