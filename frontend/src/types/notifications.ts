import type { Id } from "./core";
import type { Notification } from "./index";

export type NotificationPreference = {
  id: Id;
  business: Id;
  user: Id;
  user_email?: string | null;
  user_name?: string | null;
  category: Notification["category"];
  in_app_enabled: boolean;
  created_at: string;
  updated_at: string;
};
