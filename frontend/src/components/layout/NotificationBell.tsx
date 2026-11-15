import { Link, useNavigate } from "react-router";
import { ArrowRight, Bell, Check, CheckCheck } from "lucide-react";
import type { Dispatch, SetStateAction } from "react";
import type { useAuth } from "../../features/auth/AuthProvider";
import type { useActiveBusiness } from "../../hooks/useBusiness";
import { useNotificationBell } from "./useNotificationBell";
import { useI18n } from "../../lib/i18n";
import { formatDateTime } from "../../lib/format";
import { Button } from "../ui/Button";
import { notificationText } from "../../features/notifications/NotificationInspector";
import { ErrorState, LoadingState } from "../ui/StateViews";

type Props = {
  user: ReturnType<typeof useAuth>["user"];
  business: ReturnType<typeof useActiveBusiness>["business"];
  showNotifications: boolean;
  setShowNotifications: Dispatch<SetStateAction<boolean>>;
  setSelectedNotification: Dispatch<SetStateAction<number | null>>;
};

export function NotificationBell({ user, business, showNotifications, setShowNotifications, setSelectedNotification }: Props) {
  const { t, language } = useI18n();
  const navigate = useNavigate();
  const { notificationsRef, notifications, notificationSummary, markReadMutation,
    markAllReadMutation, unreadCount, latestNotifications, resolveNotificationRoute } = useNotificationBell({
    user, business, showNotifications, setShowNotifications,
  });
  return <div className="relative" ref={notificationsRef}>
    <Button variant="ghost" size="icon" className="relative h-11 w-11 min-h-11 min-w-11 rounded-control px-0"
      aria-label={t("header.notifications")} aria-expanded={showNotifications} aria-controls="notification-menu"
      disabled={!business} onClick={() => setShowNotifications(current => !current)} data-testid="header-notifications-trigger">
      <Bell aria-hidden="true" size={20} strokeWidth={2} />
      {unreadCount ? <span className="absolute -right-1 -top-1 min-w-5 rounded-full bg-brand-500 px-1.5 py-0.5 text-xs font-semibold text-white ring-2 ring-surface">{unreadCount > 99 ? "99+" : unreadCount}</span> : null}
    </Button>
    {showNotifications ? <section id="notification-menu" aria-label={t("header.notifications")} data-testid="notification-menu"
      className="fixed inset-x-3 top-16 flex max-h-[calc(100dvh-10rem)] flex-col overflow-hidden rounded-card border border-platforma-border bg-surface-card text-sm shadow-premium sm:absolute sm:inset-auto sm:right-0 sm:top-12 sm:max-h-[min(42rem,80dvh)] sm:w-[28rem]">
      <header className="flex shrink-0 items-center justify-between gap-[8px] border-b border-platforma-border px-[16px] py-[8px]">
        <h2 className="flex min-w-0 items-center gap-2 font-semibold text-platforma-ink">
          <span className="min-w-0 break-words sm:truncate">{t("header.notifications")}</span>
          {!notificationSummary.isError && notificationSummary.data ? <span className="shrink-0 rounded-control bg-brand-50 px-2 py-0.5 text-brand-700">{unreadCount}</span> : null}
        </h2>
        <Button variant="ghost" size="icon" className="h-[44px] w-[44px] min-h-[44px] min-w-[44px] shrink-0 text-brand-700" title={t("header.markAllRead")}
          aria-label={t("header.markAllRead")} onClick={() => markAllReadMutation.mutate()}
          disabled={!unreadCount || !business || notificationSummary.isError || notifications.isError || markAllReadMutation.isPending}>
          <CheckCheck size={20} aria-hidden="true" />
        </Button>
      </header>
      <div className="min-h-0 overflow-y-auto px-[16px]">
        {notifications.isPending ? <LoadingState /> : null}
        {notifications.isError ? <ErrorState error={notifications.error} action={<Button variant="secondary" onClick={() => void notifications.refetch()}>{t("common.retry")}</Button>} /> : null}
        {notificationSummary.isError ? <ErrorState error={notificationSummary.error} action={<Button variant="secondary" onClick={() => void notificationSummary.refetch()}>{t("common.retry")}</Button>} /> : null}
        {markReadMutation.isError || markAllReadMutation.isError ? <ErrorState error={markReadMutation.error || markAllReadMutation.error} /> : null}
        <ul className="divide-y divide-platforma-border">
          {latestNotifications.map(notification => <li key={notification.id} className="flex items-center gap-2 py-1" data-testid="notification-menu-row">
            <button type="button" disabled={markReadMutation.isPending} className="platforma-focus-ring flex min-h-16 min-w-0 flex-1 items-center gap-[12px] rounded-control py-2 text-left hover:bg-surface-hover disabled:cursor-wait"
              onClick={() => {
                if (notification.kind !== "announcement" && notification.action_url) {
                  markReadMutation.mutate(notification.id, { onSuccess: () => {
                    setShowNotifications(false);
                    navigate(resolveNotificationRoute(notification.action_url));
                  } });
                } else {
                  setSelectedNotification(notification.id);
                  setShowNotifications(false);
                }
              }}>
              <span className={`h-2 w-2 shrink-0 rounded-full ${notification.read_at ? "bg-transparent" : "bg-brand-500"}`} aria-hidden="true" />
              <span className="min-w-0 flex-1">
                <span className={`block truncate text-platforma-ink ${notification.read_at ? "font-medium" : "font-semibold"}`}>{notificationText(notification, t)}</span>
                <span className="mt-0.5 block truncate text-xs text-platforma-subtle">{notification.priority === "urgent" || notification.priority === "high" ? `${t(`notification.priority.${notification.priority}`)} · ` : ""}{notification.client_name || "CRM"} · {formatDateTime(notification.send_at, undefined, false, language)}</span>
                {!notification.read_at ? <span className="sr-only">{t("notification.filter.unread")}</span> : null}
              </span>
            </button>
            {!notification.read_at ? <Button variant="ghost" size="icon" className="h-[44px] w-[44px] min-h-[44px] min-w-[44px] shrink-0" title={t("notification.markRead")}
              aria-label={t("notification.markRead")} disabled={markReadMutation.isPending}
              onClick={() => markReadMutation.mutate(notification.id)}><Check size={18} aria-hidden="true" /></Button> : <span className="w-[44px] shrink-0" />}
          </li>)}
        </ul>
        {!notifications.isPending && !notifications.isError && !latestNotifications.length ? <p className="py-6 text-platforma-subtle">{t("header.noNotifications")}</p> : null}
      </div>
      <Link to="/app/notifications" onClick={() => setShowNotifications(false)}
        className="platforma-focus-ring flex min-h-12 shrink-0 items-center justify-between border-t border-platforma-border px-4 py-3 font-semibold text-brand-700 hover:bg-surface-hover">
        {t("notification.openCenter")}<ArrowRight size={20} aria-hidden="true" />
      </Link>
    </section> : null}
  </div>;
}
