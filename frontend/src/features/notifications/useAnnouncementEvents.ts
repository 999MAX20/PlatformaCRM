import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { subscribeAnnouncementEvents } from "../../api/announcementEvents";
import type { Id } from "../../types";

export function useAnnouncementEvents(business: Id, user: Id | undefined, enabled: boolean) {
  const client = useQueryClient();
  useEffect(() => {
    if (!enabled || !user) return;
    return subscribeAnnouncementEvents(business, {
      invalidate: () => client.invalidateQueries({ queryKey: ["announcements"] }),
      forbidden: () => Promise.all([
        client.resetQueries({ queryKey: ["announcements"] }),
        client.invalidateQueries({ queryKey: ["notifications-summary"] }),
      ]),
    });
  }, [business, user, enabled, client]);
}
