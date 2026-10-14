export type SupportStatus = "new" | "in_progress" | "waiting_clinic" | "waiting_internal" | "resolved";
export type SupportActor = { id: number; name: string };
export type SupportScope = { platform: boolean; business?: number };
export type SupportPage<T> = { count: number; next: string | null; previous: string | null; results: T[] };
export type SupportCase = {
  id: number; number: string; business: number; business_name: string; business_timezone: string;
  subject: string; source: "clinic" | "platform"; status: SupportStatus;
  author: SupportActor; contact: SupportActor; assignee: (SupportActor & { available?: boolean }) | null;
  version: number; created_at: string; updated_at: string; last_public_message_at: string | null;
  resolved_at: string | null; unread_count: number;
  available_actions: { reply: boolean; assign: boolean; internal_note: boolean; reopen: boolean; transitions: SupportStatus[] };
};
export type SupportMessage = { id: number; author: SupportActor; source: "clinic" | "platform"; text: string; created_at: string };
export type SupportNote = Omit<SupportMessage, "source">;
export type SupportEvent = {
  id: number; actor: SupportActor; kind: "created" | "assigned" | "transitioned" | "reopened";
  old_value: string; new_value: string; reason: string; created_at: string;
};
export type SupportFilters = { business?: number; search?: string; status?: string; assignee?: string; unread?: boolean; page?: number; page_size?: number };
