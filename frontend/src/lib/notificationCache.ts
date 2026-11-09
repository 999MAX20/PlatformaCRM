import type { QueryClient } from "@tanstack/react-query";

/** A receipt changes the personal feed as well as the owner's monitoring views. */
export async function invalidateNotificationReceipts(client: QueryClient) {
  await Promise.all([
    "notifications", "notifications-summary", "notification-detail", "announcements",
  ].map(key => client.invalidateQueries({ queryKey: [key] })));
}
