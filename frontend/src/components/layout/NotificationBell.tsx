import { useNavigate } from "react-router";
import type { useAuth } from "../../features/auth/AuthProvider";
import { useNotificationBell } from "./useNotificationBell";

import { Bell, Check, Sparkles } from "lucide-react";

import { Link } from "react-router";

import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { formatDateTime } from "../../lib/format";
import { Button } from "../ui/Button";

import { notificationText } from "../../features/notifications/NotificationInspector";
import { ErrorState, LoadingState } from "../ui/StateViews";

import type { Dispatch, SetStateAction } from "react";
type Props = {
  user: ReturnType<typeof useAuth>["user"];
  business: ReturnType<typeof useActiveBusiness>["business"];
  showNotifications: boolean;
  setShowNotifications: Dispatch<SetStateAction<boolean>>;
  setSelectedNotification: Dispatch<SetStateAction<number | null>>;
};
export function NotificationBell({
  user,
  business,
  showNotifications,
  setShowNotifications,
  setSelectedNotification,
}: Props) {
  const { t, language } = useI18n();
  const navigate = useNavigate();
  const {
    notificationsRef,
    notifications,
    notificationSummary,
    markReadMutation,
    markAllReadMutation,
    unreadCount,
    latestNotifications,
    groupedNotifications,
    categoryLabels,
    priorityClass,
    priorityLabels,
    notificationAudienceLabel,
    resolveNotificationRoute,
  } = useNotificationBell({
    user,
    business,
    t,
    showNotifications,
    setShowNotifications,
  });
  return (
    <div className="relative" ref={notificationsRef}>
      <Button
        variant="ghost"
        size="icon"
        className="relative h-10 w-10 min-h-10 min-w-10 rounded-control px-0"
        aria-label={t("header.notifications")}
        disabled={!business}
        onClick={() => setShowNotifications((current) => !current)}
        data-testid="header-notifications-trigger"
      >
        <Bell aria-hidden="true" size={20} strokeWidth={2} />
        {unreadCount ? (
          <span className="absolute -right-1 -top-1 min-w-5 rounded-full bg-brand-500 px-1.5 py-0.5 text-[10px] font-semibold text-white ring-2 ring-surface">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        ) : null}
      </Button>
      {showNotifications ? (
        <div className="fixed inset-x-3 top-16 max-h-[76vh] overflow-y-auto rounded-card border border-platforma-border bg-surface-card p-4 text-sm shadow-premium sm:absolute sm:inset-auto sm:right-0 sm:top-11 sm:w-[26rem]">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold text-platforma-ink">
                {t("header.notifications")}
              </p>
              <p className="mt-0.5 text-xs text-platforma-faint">
                {notificationSummary.isPending ? t("common.loading") : notificationSummary.isError || !notificationSummary.data ? t("serviceStatus.countsUnavailable") : t("header.notificationsSummary", {
                  due: notificationSummary.data.due,
                  urgent: notificationSummary.data.urgent,
                })}
              </p>
            </div>
            <Button
              variant="ghost"
              className="h-9 rounded-full px-3 text-xs"
              onClick={() => markAllReadMutation.mutate()}
              disabled={
                !unreadCount || !business || notificationSummary.isError || notifications.isError || markAllReadMutation.isPending
              }
            >
              <Check size={14} /> {t("header.markAllRead")}
            </Button>
          </div>
          <div className="mt-4 space-y-4">
            {notifications.isPending ? <LoadingState /> : null}
            {notifications.isError ? (
              <ErrorState error={notifications.error} action={<Button variant="secondary" onClick={() => void notifications.refetch()}>{t("common.retry")}</Button>} />
            ) : null}
            {notificationSummary.isError ? (
              <ErrorState error={notificationSummary.error} action={<Button variant="secondary" onClick={() => void notificationSummary.refetch()}>{t("common.retry")}</Button>} />
            ) : null}
            {markReadMutation.isError || markAllReadMutation.isError ? (
              <ErrorState
                error={markReadMutation.error || markAllReadMutation.error}
              />
            ) : null}
            {Object.entries(groupedNotifications).map(([category, items]) => (
              <div key={category} className="space-y-2">
                <p className="text-xs font-semibold text-platforma-faint">
                  {categoryLabels[category] || category}
                </p>
                {items.map((notification) => (
                  <div
                    key={notification.id}
                    className={`rounded-card border p-3 ${notification.read_at ? "border-platforma-border bg-surface-card" : "border-brand-100 bg-brand-50/45"}`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="mb-1 flex flex-wrap items-center gap-2">
                          {!notification.read_at ? (
                            <span className="h-2 w-2 rounded-full bg-brand-500" />
                          ) : null}
                          <span
                            className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${priorityClass[notification.priority] || priorityClass.normal}`}
                          >
                            {priorityLabels[notification.priority] ||
                              notification.priority}
                          </span>
                        </div>
                        <p className="line-clamp-2 font-semibold text-platforma-ink">
                          {notificationText(notification, t)}
                        </p>
                        <p className="mt-1 text-xs text-platforma-faint">
                          {notificationAudienceLabel(notification)} ·{" "}
                          {notification.client_name || "CRM"} ·{" "}
                          {formatDateTime(
                            notification.send_at,
                            undefined,
                            false,
                            language,
                          )}
                        </p>
                      </div>
                      <span className="text-xs text-platforma-subtle">
                        {t(
                          notification.kind === "announcement"
                            ? "notification.announcement"
                            : "notification.workItem",
                        )}
                      </span>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {notification.kind === "announcement" ? (
                        <Button
                          variant="secondary"
                          className="h-9 rounded-full px-3 text-xs"
                          onClick={() => {
                            setSelectedNotification(notification.id);
                            setShowNotifications(false);
                          }}
                        >
                          {t("common.open")}
                        </Button>
                      ) : null}
                      {notification.action_url ? (
                        <Button
                          variant="secondary"
                          className="h-9 rounded-full px-3 text-xs"
                          onClick={() => {
                            markReadMutation.mutate(notification.id);
                            setShowNotifications(false);
                            navigate(
                              resolveNotificationRoute(notification.action_url),
                            );
                          }}
                        >
                          <Sparkles size={14} />
                          {notification.action_label || t("common.open")}
                        </Button>
                      ) : null}
                      {!notification.read_at ? (
                        <Button
                          variant="ghost"
                          className="h-9 rounded-full px-3 text-xs"
                          onClick={() =>
                            markReadMutation.mutate(notification.id)
                          }
                        >
                          <Check size={15} />
                          {t("notification.read")}
                        </Button>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            ))}
            {!notifications.isPending &&
            !notifications.isError &&
            !latestNotifications.length ? (
              <p className="rounded-card bg-surface-muted p-4 leading-6 text-platforma-subtle">
                {t("header.noNotifications")}
              </p>
            ) : null}
          </div>
          <Link
            to="/app/notifications"
            onClick={() => setShowNotifications(false)}
            className="platforma-focus-ring mt-4 block rounded-control bg-brand-500 px-4 py-3 text-center text-sm font-semibold text-white ring-1 ring-brand-600/10 transition hover:bg-brand-600"
          >
            {t("notification.openCenter")}
          </Link>
        </div>
      ) : null}
    </div>
  );
}
