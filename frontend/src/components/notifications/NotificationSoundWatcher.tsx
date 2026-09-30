import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { notificationsApi } from "../../api/notifications";
import { playNotificationSound, unlockNotificationSound } from "../../lib/notificationSound";
import { realtimeIntervals, realtimeQueryOptions } from "../../lib/realtime";
import type { Id } from "../../types";

// Mount only while enabled. The first fresh result is a silent baseline, so
// opening CRM, switching accounts or unmuting never replays an old backlog.
export function NotificationSoundWatcher({ userId, businessId }: { userId: Id; businessId: Id }) {
  const baseline = useRef<{ seen: Set<string>; latest: number } | null>(null);
  const notifications = useQuery({
    queryKey: ["notifications", "bell", businessId, userId],
    queryFn: () => notificationsApi.list({ surface: "bell", business: businessId }),
    refetchInterval: realtimeIntervals.notificationsMs,
    refetchIntervalInBackground: true,
    refetchOnMount: "always",
    ...realtimeQueryOptions,
  });

  useEffect(() => {
    const unlock = () => { void unlockNotificationSound().catch(() => undefined); };
    window.addEventListener("pointerdown", unlock);
    window.addEventListener("keydown", unlock);
    return () => {
      window.removeEventListener("pointerdown", unlock);
      window.removeEventListener("keydown", unlock);
    };
  }, []);

  useEffect(() => {
    if (!notifications.isFetchedAfterMount || !notifications.data) return;
    const items = notifications.data;
    const latest = Math.max(0, ...items.map((item) => Date.parse(item.send_at) || 0));
    const previous = baseline.current;
    baseline.current = {
      seen: new Set([...(previous?.seen || []), ...items.map((item) => String(item.id))].slice(-2000)),
      latest: Math.max(previous?.latest || 0, latest),
    };
    if (!previous) return;
    const arrivals = items.filter((item) => !item.read_at && !previous.seen.has(String(item.id)) && Date.parse(item.send_at) >= previous.latest);
    if (!arrivals.length) return;

    // One chime for a batch. Share its IDs across tabs to avoid repeating the
    // same alert in every open copy of CRM; storage contains IDs, not messages.
    const key = `platforma:notification-sound-seen:${userId}:${businessId}`;
    let cancelled = false;
    const playBatch = () => {
      if (cancelled) return;
      try {
        const played = JSON.parse(localStorage.getItem(key) || "[]") as string[];
        if (!Array.isArray(played)) return;
        const fresh = arrivals.filter((item) => !played.includes(String(item.id)));
        if (!fresh.length) return;
        if (playNotificationSound()) {
          localStorage.setItem(key, JSON.stringify([...played, ...fresh.map((item) => String(item.id))].slice(-200)));
        }
      } catch {
        // Audio/storage restrictions must never interrupt the notification UI.
      }
    };
    if (navigator.locks) void navigator.locks.request(key, playBatch).catch(() => undefined);
    else playBatch();
    return () => { cancelled = true; };
  }, [notifications.data, notifications.isFetchedAfterMount, userId, businessId]);

  return null;
}
