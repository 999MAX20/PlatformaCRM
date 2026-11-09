import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
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

export function NotificationInspector({ id, business, onClose }: { id: Id; business: Id; onClose: () => void }) {
  const { t, language } = useI18n();
  const { user } = useAuth();
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
  const notification = detail.data;
  const mutationError = opened.error || acknowledge.error || unread.error;
  const accessLost = mutationError && ["permission", "not_found", "authentication"].includes(normalizeAppError(mutationError).category);
  return <Modal title={t("header.notifications")} open onClose={onClose} testId="notification-inspector">
    {accessLost ? <ErrorState error={mutationError} /> : detail.isPending ? <LoadingState /> : detail.isError ? <ErrorState error={detail.error}
      action={<Button variant="secondary" onClick={() => void detail.refetch()}>{t("common.retry")}</Button>} /> : notification ? <div className="space-y-4">
      <p className="text-xs text-platforma-faint">{t(notification.kind === "announcement" ? "notification.announcement" : "notification.workItem")} · {formatDateTime(notification.send_at, undefined, false, language)}</p>
      <p className="whitespace-pre-wrap break-words text-sm text-platforma-ink">{notificationText(notification, t)}</p>
      {notification.author_name ? <p className="text-xs text-platforma-subtle">{notification.author_name}</p> : null}
      {mutationError ? <ErrorState error={mutationError} /> : null}
      {opened.isError ? <Button variant="secondary" onClick={() => opened.mutate()}>{t("common.retry")}</Button> : null}
      {notification.acknowledged_at ? <p role="status" className="text-sm text-platforma-subtle">{t("notification.acknowledged")} · {formatDateTime(notification.acknowledged_at, undefined, false, language)}</p> : null}
      <div className="flex flex-wrap gap-2">
        {notification.kind === "announcement" && !notification.acknowledged_at ? <Button
          onClick={() => acknowledge.mutate()} disabled={!notification.opened_at || opened.isPending || acknowledge.isPending}
          isLoading={acknowledge.isPending}>{t("notification.acknowledge")}</Button> : null}
        {notification.action_url ? <Link to={notification.action_url} onClick={onClose}
          className="platforma-focus-ring inline-flex min-h-10 items-center rounded-control bg-brand-500 px-4 text-sm font-semibold text-white">{t("common.open")}</Link> : null}
        {notification.read_at ? <Button variant="secondary" onClick={() => unread.mutate()} isLoading={unread.isPending}>{t("notification.markUnread")}</Button> : null}
      </div>
    </div> : null}
  </Modal>;
}
