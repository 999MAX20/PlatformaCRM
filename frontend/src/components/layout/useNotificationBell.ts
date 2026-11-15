import { useEffect, useRef } from "react";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { invalidateNotificationReceipts } from "../../lib/notificationCache";
import { notificationsApi } from "../../api/notifications";

import { useAuth } from "../../features/auth/AuthProvider";
import { useActiveBusiness } from "../../hooks/useBusiness";

import { realtimeIntervals, realtimeQueryOptions } from "../../lib/realtime";

import type { Id } from "../../types";
import type { Dispatch, SetStateAction } from "react";
type Args = {
  user: ReturnType<typeof useAuth>["user"];
  business: ReturnType<typeof useActiveBusiness>["business"];
  showNotifications: boolean;
  setShowNotifications: Dispatch<SetStateAction<boolean>>;
};
export function useNotificationBell({
  user,
  business,
  showNotifications,
  setShowNotifications,
}: Args) {
  const queryClient = useQueryClient();
  const notificationsRef = useRef<HTMLDivElement | null>(null);
  const notifications = useQuery({
    queryKey: ["notifications", "bell", business?.id, user?.id, "unread"],
    queryFn: () =>
      notificationsApi.list({ surface: "bell", business: business?.id, order: "unread" }),
    enabled: Boolean(user && business) && showNotifications,
    ...realtimeQueryOptions,
  });
  const notificationSummary = useQuery({
    queryKey: ["notifications-summary", "bell", business?.id, user?.id],
    queryFn: () =>
      notificationsApi.summary({ surface: "bell", business: business?.id }),
    enabled: Boolean(user && business),
    refetchInterval: realtimeIntervals.notificationsMs,
    ...realtimeQueryOptions,
  });
  const markReadMutation = useMutation({
    mutationFn: (id: Id) => notificationsApi.markRead(id, business?.id),
    onSuccess: () => invalidateNotificationReceipts(queryClient),
  });
  const markAllReadMutation = useMutation({
    mutationFn: () =>
      notificationsApi.markAllRead({ surface: "bell", business: business?.id }),
    onSuccess: () => invalidateNotificationReceipts(queryClient),
  });
  const unreadCount = notificationSummary.isError
    ? 0
    : (notificationSummary.data?.unread ?? 0);
  const latestNotifications = [
    ...(!notifications.isError ? notifications.data || [] : []),
  ]
    .sort(
      (a, b) =>
        Number(!b.read_at) - Number(!a.read_at) ||
        new Date(b.send_at).getTime() - new Date(a.send_at).getTime(),
    )
    .slice(0, 6);
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
        notificationsRef.current?.querySelector<HTMLButtonElement>("[data-testid='header-notifications-trigger']")?.focus();
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
    legacyNotificationRoutes,
    resolveNotificationRoute,
  };
}
