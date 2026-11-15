import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Check, SlidersHorizontal } from "lucide-react";
import { invalidateNotificationReceipts } from "../../lib/notificationCache";
import { notificationsApi, type PersonalFeedFilters } from "../../api/notifications";
import { normalizeAppError } from "../../api/appError";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import { Tabs } from "../../components/ui/Tabs";
import { EmptyState, ErrorState, ForbiddenState, LoadingState } from "../../components/ui/StateViews";
import { usePageLoading } from "../../components/ui/PageLoadingBoundary";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useMediaQuery } from "../../hooks/useMediaQuery";
import { formatDateTime } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import { realtimeIntervals } from "../../lib/realtime";
import type { Id } from "../../types";
import { useAuth } from "../auth/AuthProvider";
import { AnnouncementManager, NotificationPagination } from "./AnnouncementManager";
import { NotificationInspector, notificationText } from "./NotificationInspector";
import { NotificationFilters, type FeedView } from "./NotificationFilters";

export function NotificationsPage() {
  const { business, isLoading, error } = useActiveBusiness();
  usePageLoading(isLoading);
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
  const [view, setView] = useState<FeedView>("all");
  const [filters, setFilters] = useState<PersonalFeedFilters>({ period: "all", order: "newest" });
  const [showFilters, setShowFilters] = useState(false);
  const wide = useMediaQuery("(min-width: 1280px)");
  const lastTrigger = useRef<HTMLButtonElement | null>(null);
  const listTitle = useRef<HTMLHeadingElement | null>(null);
  useEffect(() => { setPageHeader({ title: t("header.notifications") }); return () => setPageHeader(null); }, [setPageHeader, t]);
  const summary = useQuery({ queryKey: ["notifications-summary", "bell", business, user?.id],
    queryFn: () => notificationsApi.summary({ surface: "bell", business }), refetchInterval: realtimeIntervals.notificationsMs,
    refetchOnWindowFocus: true, retry: false });
  const feedFilters = { ...filters, unread: view === "unread" ? true : undefined, awaiting_ack: view === "awaiting" ? true : undefined };
  const feed = useQuery({ queryKey: ["notifications", "page", business, user?.id, page, feedFilters],
    queryFn: () => notificationsApi.personalPage(business, page, feedFilters), enabled: tab === "feed",
    refetchInterval: realtimeIntervals.notificationsMs, refetchOnWindowFocus: true, retry: false });
  const readAll = useMutation({ mutationFn: () => notificationsApi.markAllRead({ business, surface: "bell" }), onSuccess: () => invalidateNotificationReceipts(client) });
  const read = useMutation({ mutationFn: (id: Id) => notificationsApi.markRead(id, business), onSuccess: () => invalidateNotificationReceipts(client) });
  usePageLoading(summary.isLoading || (tab === "feed" && feed.isLoading));
  const canManage = !summary.isError && summary.data?.can_manage_announcements;
  const managementVisible = tab === "announcements" && canManage;
  useEffect(() => { if (!canManage && tab === "announcements") setTab("feed"); }, [canManage, tab]);
  useEffect(() => {
    if (page > 1 && ((feed.isSuccess && feed.data.results.length === 0) || (feed.isError && normalizeAppError(feed.error).category === "not_found"))) setPage(1);
  }, [feed.isSuccess, feed.isError, feed.error, feed.data, page]);
  function closeDetail() {
    setSelected(null);
    requestAnimationFrame(() => { if (lastTrigger.current?.isConnected) lastTrigger.current.focus(); else listTitle.current?.focus(); });
  }
  function changeFilters(next: PersonalFeedFilters) { setFilters(next); setPage(1); }
  const filterContent = <NotificationFilters view={view} filters={filters} unread={summary.isError ? undefined : summary.data?.unread}
    onView={next => { setView(next); setPage(1); }} onFilters={changeFilters} />;
  return <div className="min-w-0 bg-surface-card" data-testid="notifications-page">
    {summary.isError ? <ErrorState error={summary.error} action={<Button variant="secondary" onClick={() => void summary.refetch()}>{t("common.retry")}</Button>} /> : null}
    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-platforma-border">
      <Tabs value={tab} onChange={next => { setTab(next); setSelected(null); }} appearance="underline" ariaLabel={t("header.notifications")}
        idPrefix="notification-tabs" className="max-w-full border-0 [&_button]:min-h-12"
        options={[{ value: "feed", label: t("notification.myFeed") }, ...(canManage ? [{ value: "announcements" as const, label: t("notification.announcements") }] : [])]} />
      {!managementVisible ? <Button variant="ghost" className="min-h-11 text-brand-700" onClick={() => readAll.mutate()} disabled={!summary.data?.unread || summary.isError || feed.isError} isLoading={readAll.isPending}>{t("header.markAllRead")}</Button> : null}
    </div>
    {managementVisible ? <div role="tabpanel" id="notification-tabs-panel-announcements" aria-labelledby="notification-tabs-tab-announcements" className="py-4"><AnnouncementManager business={business} /></div> : <div role="tabpanel" id="notification-tabs-panel-feed" aria-labelledby="notification-tabs-tab-feed">
      {readAll.isError || read.isError ? <ErrorState error={readAll.error || read.error} /> : null}
      {readAll.isSuccess ? <p role="status" className="px-4 py-2 text-sm text-platforma-subtle">{t("notification.readAllResult", { count: readAll.data.updated })}</p> : null}
      <div className={`grid min-h-[65vh] min-w-0 md:grid-cols-[13rem_minmax(0,1fr)] ${selected && wide ? "xl:grid-cols-[13rem_minmax(0,1fr)_minmax(19rem,0.85fr)]" : ""}`}>
        <aside className="border-b border-platforma-border p-3 md:border-b-0 md:border-r md:py-5" aria-label={t("notification.filters")}>
          <Button variant="ghost" className="min-h-11 w-full justify-between md:hidden" aria-expanded={showFilters} aria-controls="notification-filter-controls" onClick={() => setShowFilters(value => !value)}>
            {t("notification.filters")}<SlidersHorizontal size={18} aria-hidden="true" />
          </Button>
          <div id="notification-filter-controls" className={showFilters ? "pt-3 md:pt-0" : "hidden md:block"}>{filterContent}</div>
        </aside>
        <section className="min-w-0" aria-label={t("notification.myFeed")}>
          <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-4">
            <h2 ref={listTitle} tabIndex={-1} className="text-lg font-semibold text-platforma-ink">{t(`notification.filter.${view}`)}</h2>
            <div className="w-40"><Select aria-label={t("notification.order")} value={filters.order || "newest"}
              onChange={event => changeFilters({ ...filters, order: event.target.value as PersonalFeedFilters["order"] })}
              options={["newest", "oldest"].map(value => ({ value, label: t(`notification.order.${value}`) }))} /></div>
          </div>
          {feed.isPending ? <LoadingState /> : feed.isError ? <ErrorState error={feed.error}
            action={<Button variant="secondary" onClick={() => void feed.refetch()}>{t("common.retry")}</Button>} /> : <>
            <ul className="divide-y divide-platforma-border px-2">
              {feed.data?.results.map(notification => <li key={notification.id} data-testid="notification-feed-row"
                className={`flex min-w-0 items-center gap-1 border-l-[3px] px-1 ${selected === notification.id ? "border-l-brand-500 bg-brand-50" : "border-l-transparent"}`}>
                <button type="button" aria-pressed={selected === notification.id}
                  className="platforma-focus-ring flex min-h-[4.5rem] min-w-0 flex-1 items-center gap-3 rounded-control px-2 py-3 text-left hover:bg-surface-hover"
                  onClick={event => { lastTrigger.current = event.currentTarget; setSelected(notification.id); }}>
                  <span className={`h-2 w-2 shrink-0 rounded-full ${notification.read_at ? "bg-transparent" : "bg-brand-500"}`} aria-hidden="true" />
                  <span className="min-w-0 flex-1">
                    <span className={`block truncate text-sm text-platforma-ink ${notification.read_at ? "font-medium" : "font-semibold"}`}>{notificationText(notification, t)}</span>
                    <span className="mt-0.5 block truncate text-xs text-platforma-subtle">{notification.client_name || "CRM"} · {t(notification.kind === "announcement" ? "notification.announcement" : `notification.category.${notification.category === "ai_alerts" ? "aiAlerts" : notification.category}`)}</span>
                    <span className="mt-1 block text-xs text-platforma-subtle lg:hidden">{formatDateTime(notification.send_at, undefined, false, language)}</span>
                    {!notification.read_at ? <span className="sr-only">{t("notification.filter.unread")}</span> : null}
                    {notification.acknowledged_at ? <span className="mt-1 block text-xs text-platforma-subtle">{t("notification.acknowledged")}</span> : null}
                  </span>
                  <time className="hidden shrink-0 text-xs text-platforma-subtle lg:block" dateTime={notification.send_at}>{formatDateTime(notification.send_at, undefined, false, language)}</time>
                </button>
                {!notification.read_at ? <Button variant="ghost" size="icon" className="h-11 w-11 shrink-0" aria-label={t("notification.markRead")} title={t("notification.markRead")} disabled={read.isPending} onClick={() => read.mutate(notification.id)}><Check size={18} aria-hidden="true" /></Button> : <span className="w-11 shrink-0" />}
              </li>)}
            </ul>
            {!feed.data?.results.length ? <EmptyState title={t("header.noNotifications")} /> : null}
            <div className="p-4"><NotificationPagination page={page} previous={Boolean(feed.data?.previous)} next={Boolean(feed.data?.next)} onPage={setPage} /></div>
          </>}
        </section>
        {selected ? <NotificationInspector key={`${business}:${selected}`} id={selected} business={business} onClose={closeDetail} inline={wide} /> : null}
      </div>
    </div>}
  </div>;
}
