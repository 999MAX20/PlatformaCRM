import { useEffect, useRef } from "react";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notificationsApi } from "../../api/notifications";

import { useAuth } from "../../features/auth/AuthProvider";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";

import { realtimeIntervals, realtimeQueryOptions } from "../../lib/realtime";

import type { Dispatch, SetStateAction } from "react";
type Args = {
  user: ReturnType<typeof useAuth>["user"];
  business: ReturnType<typeof useActiveBusiness>["business"];
  t: ReturnType<typeof useI18n>["t"];
  showNotifications: boolean;
  setShowNotifications: Dispatch<SetStateAction<boolean>>;
};
export function useNotificationBell({
  user,
  business,
  t,
  showNotifications,
  setShowNotifications,
}: Args) {
  const queryClient = useQueryClient();
  const notificationsRef = useRef<HTMLDivElement | null>(null);
  const notifications = useQuery({
    queryKey: ["notifications", "bell", business?.id, user?.id],
    queryFn: () =>
      notificationsApi.list({ surface: "bell", business: business?.id }),
    enabled: Boolean(user) && showNotifications,
    ...realtimeQueryOptions,
  });
  const notificationSummary = useQuery({
    queryKey: ["notifications-summary", "bell"],
    queryFn: () => notificationsApi.summary({ surface: "bell" }),
    enabled: Boolean(user),
    refetchInterval: realtimeIntervals.notificationsMs,
    ...realtimeQueryOptions,
  });
  const markReadMutation = useMutation({
    mutationFn: notificationsApi.markRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["notifications-summary"] });
    },
  });
  const markAllReadMutation = useMutation({
    mutationFn: () => notificationsApi.markAllRead({ surface: "bell" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["notifications-summary"] });
    },
  });
  const unreadCount = notificationSummary.data?.unread ?? 0;
  const latestNotifications = [...(notifications.data || [])]
    .sort(
      (a, b) =>
        Number(!b.read_at) - Number(!a.read_at) ||
        new Date(b.send_at).getTime() - new Date(a.send_at).getTime(),
    )
    .slice(0, 7);
  const groupedNotifications = latestNotifications.reduce<
    Record<string, typeof latestNotifications>
  >((acc, notification) => {
    const key = notification.category || "system";
    acc[key] = acc[key] || [];
    acc[key].push(notification);
    return acc;
  }, {});
  const categoryLabels: Record<string, string> = {
    sales: t("notification.category.sales"),
    finance: t("notification.category.finance"),
    system: t("notification.category.system"),
    ai_alerts: t("notification.category.aiAlerts"),
    outreach: t("notification.category.outreach"),
    tasks: t("notification.category.tasks"),
  };
  const priorityClass: Record<string, string> = {
    low: "bg-surface-muted text-platforma-faint",
    normal: "bg-brand-50 text-brand-700",
    high: "bg-[var(--platforma-warning-soft)] text-platforma-warning",
    urgent: "bg-[var(--platforma-danger-soft)] text-platforma-danger",
  };
  const priorityLabels: Record<string, string> = {
    low: t("notification.priority.low"),
    normal: t("notification.priority.normal"),
    high: t("notification.priority.high"),
    urgent: t("notification.priority.urgent"),
  };
  const legacyNotificationRoutes: Record<string, string> = {
    "/leads": "/app/leads",
    "/clients": "/app/clients",
    "/deals": "/app/deals",
    "/tasks": "/app/tasks",
    "/calendar": "/app/calendar",
    "/appointments": "/app/calendar",
    "/conversations": "/app/conversations",
    "/integrations": "/app/integrations",
    "/settings": "/app/settings",
  };
  function notificationAudienceLabel(
    notification: (typeof latestNotifications)[number],
  ) {
    if (notification.recipient && notification.recipient === user?.id)
      return t("notification.toMe");
    if (notification.recipient_name || notification.recipient_email) {
      return t("notification.toUser", {
        name: notification.recipient_name || notification.recipient_email || "",
      });
    }
    return t("notification.toTeam");
  }
  function resolveNotificationRoute(url: string) {
    const [path, query = ""] = url.split("?");
    const route = legacyNotificationRoutes[path] || url;
    return query && legacyNotificationRoutes[path]
      ? `${route}?${query}`
      : route;
  }
  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      if (notificationsRef.current?.contains(event.target as Node)) return;
      setShowNotifications(false);
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setShowNotifications(false);
      }
    }

    if (showNotifications) {
      document.addEventListener("pointerdown", handlePointerDown);
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [showNotifications]);
  return {
    queryClient,
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
    legacyNotificationRoutes,
    notificationAudienceLabel,
    resolveNotificationRoute,
  };
}
