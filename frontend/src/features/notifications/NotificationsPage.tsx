import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { invalidateNotificationReceipts } from "../../lib/notificationCache";
import { notificationsApi } from "../../api/notifications";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { Button } from "../../components/ui/Button";
import { EmptyState, ErrorState, ForbiddenState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { formatDateTime } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import { realtimeIntervals } from "../../lib/realtime";
import type { Id } from "../../types";
import { useAuth } from "../auth/AuthProvider";
import { AnnouncementManager, NotificationPagination } from "./AnnouncementManager";
import { NotificationInspector, notificationText } from "./NotificationInspector";

export function NotificationsPage() {
  const { business, isLoading, error } = useActiveBusiness();
  const { user } = useAuth();
  return business && user ? <PersonalNotificationPage key={`${business.id}:${user.id}`} business={business.id} />
    : isLoading ? <LoadingState /> : error ? <ErrorState error={error} /> : <ForbiddenState />;
}

function PersonalNotificationPage({ business }: { business: Id }) {
  const { t, language } = useI18n();
  const { user } = useAuth();
  const { setPageHeader } = usePageHeader();
  const client = useQueryClient();
  const [page, setPage] = useState(1);
  const [tab, setTab] = useState<"feed" | "announcements">("feed");
  const [selected, setSelected] = useState<Id | null>(null);
  useEffect(() => { setPageHeader({ title: t("header.notifications") }); return () => setPageHeader(null); }, [setPageHeader, t]);
  const summary = useQuery({ queryKey: ["notifications-summary", "bell", business, user?.id],
    queryFn: () => notificationsApi.summary({ surface: "bell", business }), refetchInterval: realtimeIntervals.notificationsMs,
    refetchOnWindowFocus: true, retry: false });
  const feed = useQuery({ queryKey: ["notifications", "page", business, user?.id, page],
    queryFn: () => notificationsApi.personalPage(business, page), enabled: tab === "feed",
    refetchInterval: realtimeIntervals.notificationsMs, refetchOnWindowFocus: true, retry: false });
  const readAll = useMutation({ mutationFn: () => notificationsApi.markAllRead({ business, surface: "bell" }), onSuccess: () => invalidateNotificationReceipts(client) });
  const canManage = !summary.isError && summary.data?.can_manage_announcements;
  const managementVisible = tab === "announcements" && canManage;
  useEffect(() => { if (!canManage && tab === "announcements") setTab("feed"); }, [canManage, tab]);
  return <div className="space-y-5" data-testid="notifications-page">
    {summary.isError ? <ErrorState error={summary.error} /> : null}
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-wrap gap-2" role="group" aria-label={t("header.notifications")}>
        <Button variant={tab === "feed" ? "primary" : "secondary"} aria-pressed={tab === "feed"} onClick={() => setTab("feed")}>{t("notification.myFeed")}</Button>
        {canManage ? <Button variant={tab === "announcements" ? "primary" : "secondary"} aria-pressed={tab === "announcements"} onClick={() => setTab("announcements")}>{t("notification.announcements")}</Button> : null}
      </div>
      {!managementVisible ? <Button variant="secondary" onClick={() => readAll.mutate()} disabled={!summary.data?.unread || summary.isError} isLoading={readAll.isPending}>{t("header.markAllRead")}</Button> : null}
    </div>
    {managementVisible ? <AnnouncementManager business={business} /> : <>
      {readAll.isError ? <ErrorState error={readAll.error} /> : null}
      {readAll.isSuccess ? <p role="status" className="text-sm text-platforma-subtle">{t("notification.readAllResult", { count: readAll.data.updated })}</p> : null}
      {feed.isPending ? <LoadingState /> : feed.isError ? <ErrorState error={feed.error}
        action={<Button variant="secondary" onClick={() => void feed.refetch()}>{t("common.retry")}</Button>} /> : <div className="space-y-3">
        {feed.data?.results.map(notification => <article key={notification.id} className={`rounded-card border p-4 ${notification.read_at ? "border-platforma-border bg-surface-card" : "border-brand-100 bg-brand-50/45"}`}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 flex-1 space-y-2">
              <p className="text-xs text-platforma-subtle">{t(notification.kind === "announcement" ? "notification.announcement" : "notification.workItem")} · {formatDateTime(notification.send_at, undefined, false, language)}</p>
              <p className="line-clamp-3 whitespace-pre-wrap break-words text-sm font-semibold text-platforma-ink">{notificationText(notification, t)}</p>
              {notification.acknowledged_at ? <p className="text-xs text-platforma-subtle">{t("notification.acknowledged")} · {formatDateTime(notification.acknowledged_at, undefined, false, language)}</p> : null}
            </div>
            <Button variant="secondary" onClick={() => setSelected(notification.id)}>{t("common.open")}</Button>
          </div>
        </article>)}
        {!feed.data?.results.length ? <EmptyState title={t("header.noNotifications")} /> : null}
        <NotificationPagination page={page} previous={Boolean(feed.data?.previous)} next={Boolean(feed.data?.next)} onPage={setPage} />
      </div>}
    </>}
    {selected ? <NotificationInspector key={`${business}:${selected}`} id={selected} business={business} onClose={() => setSelected(null)} /> : null}
  </div>;
}
