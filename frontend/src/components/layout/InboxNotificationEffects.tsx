import { useEffect, useRef, useState } from "react";

import { useNavigate } from "react-router";
import { useQuery } from "@tanstack/react-query";

import { inboxApi } from "../../api/inbox";
import { useAuth } from "../../features/auth/AuthProvider";
import { useActiveBusiness } from "../../hooks/useBusiness";

import { hasPermission } from "../../lib/permissions";
import { realtimeIntervals, realtimeQueryOptions } from "../../lib/realtime";

import { useNotificationSoundPreference } from "../../lib/notificationSound";
import { NotificationSoundWatcher } from "../notifications/NotificationSoundWatcher";
import { UnreadMessagesNotice } from "../notifications/UnreadMessagesNotice";
type Props = {
  user: ReturnType<typeof useAuth>["user"];
  business: ReturnType<typeof useActiveBusiness>["business"];
  activeMembership:
    | NonNullable<
        NonNullable<ReturnType<typeof useAuth>["user"]>["memberships"]
      >[number]
    | undefined;
};
export function InboxNotificationEffects({
  user,
  business,
  activeMembership,
}: Props) {
  const navigate = useNavigate();
  const soundEnabled = useNotificationSoundPreference(user?.id);
  const [chatToastOpen, setChatToastOpen] = useState(false);
  const previousUnreadMessagesRef = useRef<number | null>(null);
  const inboxSummary = useQuery({
    queryKey: ["inbox-summary", business?.id],
    queryFn: inboxApi.getSummary,
    enabled:
      Boolean(user) &&
      Boolean(business?.id) &&
      hasPermission(user, business?.id, "conversations"),
    refetchInterval: realtimeIntervals.inboxConversationsMs,
    ...realtimeQueryOptions,
  });
  const unreadChatMessages =
    inboxSummary.data?.unread_messages ?? inboxSummary.data?.unread ?? 0;
  const receivesChatToasts = Boolean(
    user &&
    activeMembership?.role !== "owner" &&
    user.role !== "business_owner",
  );
  useEffect(() => {
    const previous = previousUnreadMessagesRef.current;
    previousUnreadMessagesRef.current = unreadChatMessages;
    if (!receivesChatToasts || unreadChatMessages === 0) {
      setChatToastOpen(false);
      return;
    }
    if (previous !== null && unreadChatMessages > previous)
      setChatToastOpen(true);
  }, [receivesChatToasts, unreadChatMessages]);
  useEffect(() => {
    if (!chatToastOpen) return;
    const timer = window.setTimeout(() => setChatToastOpen(false), 6500);
    return () => window.clearTimeout(timer);
  }, [chatToastOpen, unreadChatMessages]);
  return (
    <>
      {soundEnabled &&
      user &&
      business &&
      hasPermission(user, business.id, "notifications") ? (
        <NotificationSoundWatcher
          key={`${user.id}:${business.id}`}
          userId={user.id}
          businessId={business.id}
        />
      ) : null}
      {chatToastOpen ? (
        <div className="fixed right-4 top-20 z-[90] w-[min(360px,calc(100vw-2rem))]">
          <UnreadMessagesNotice
            count={unreadChatMessages}
            onDismiss={() => setChatToastOpen(false)}
            onOpen={() => {
              setChatToastOpen(false);
              navigate("/app/conversations?unread=true");
            }}
          />
        </div>
      ) : null}
    </>
  );
}
