import { useNotificationBell } from "./useNotificationBell";

import { Bell, Check, Sparkles } from "lucide-react";

import { Link } from "react-router";
import { useNavigate } from "react-router";
import { useAuth } from "../../features/auth/AuthProvider";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { formatDateTime } from "../../lib/format";
import { Button } from "../ui/Button";

import { StatusBadge } from "../ui/StatusBadge";

import type { Dispatch, SetStateAction } from "react";
type Props = {
  user: ReturnType<typeof useAuth>["user"];
  business: ReturnType<typeof useActiveBusiness>["business"];
  showNotifications: boolean;
  setShowNotifications: Dispatch<SetStateAction<boolean>>;
};
export function NotificationBell({
  user,
  business,
  showNotifications,
  setShowNotifications,
}: Props) {
  const { t } = useI18n();
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
        onClick={() => setShowNotifications((current) => !current)}
        data-testid="header-notifications-trigger"
      >
        <Bell aria-hidden="true" size={24} strokeWidth={2.1} />
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
                {t("header.notificationsSummary", {
                  due: notificationSummary.data?.due || 0,
                  urgent: notificationSummary.data?.urgent || 0,
                })}
              </p>
            </div>
            <Button
              variant="ghost"
              className="h-9 rounded-full px-3 text-xs"
              onClick={() => markAllReadMutation.mutate()}
              disabled={!unreadCount}
            >
              <Check size={14} /> {t("header.markAllRead")}
            </Button>
          </div>
          <div className="mt-4 space-y-4">
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
                          {notification.text}
                        </p>
                        <p className="mt-1 text-xs text-platforma-faint">
                          {notificationAudienceLabel(notification)} ·{" "}
                          {notification.client_name || "CRM"} ·{" "}
                          {formatDateTime(notification.send_at)}
                        </p>
                      </div>
                      <StatusBadge status={notification.status} />
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
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
            {!latestNotifications.length ? (
              <p className="rounded-card bg-surface-muted p-4 leading-6 text-platforma-subtle">
                {t("header.noNotifications")}
              </p>
            ) : null}
          </div>
          <Link
            to="/app/tasks"
            onClick={() => setShowNotifications(false)}
            className="platforma-focus-ring mt-4 block rounded-control bg-brand-500 px-4 py-3 text-center text-sm font-semibold text-white ring-1 ring-brand-600/10 transition hover:bg-brand-600"
          >
            {t("header.openTasks")}
          </Link>
        </div>
      ) : null}
    </div>
  );
}
