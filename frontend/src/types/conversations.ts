import type { Id } from "./core";
import type { FileAttachment } from "./files";

export type BotConversation = {
  ai_safety?: { calls_used: number; calls_limit: number; calls_remaining: number; next_call_available_at: string | null; reason: string };
  id: Id;
  business: Id;
  business_name?: string;
  bot: Id;
  bot_name?: string;
  public_id: string;
  channel: "website" | "telegram" | "whatsapp" | "instagram";
  external_user_id: string;
  external_thread_id?: string;
  client: Id | null;
  client_name?: string;
  client_phone?: string;
  lead: Id | null;
  deal?: Id | null;
  assigned_to?: Id | null;
  assigned_to_email?: string;
  status: "open" | "closed" | "archived";
  priority?: "low" | "normal" | "high" | "urgent";
  bot_enabled?: boolean;
  handoff_required?: boolean;
  handoff_reason?: string;
  handoff_resume_started_at?: string | null;
  ai_resume_at?: string | null;
  last_message_at?: string | null;
  last_inbound_at?: string | null;
  last_outbound_at?: string | null;
  unread_count?: number;
  sla_minutes?: number;
  sla_due_at?: string | null;
  sla_overdue?: boolean;
  sla_overdue_minutes?: number;
  metadata_json?: Record<string, unknown>;
  last_message?: {
    id: Id;
    direction: "inbound" | "outbound";
    sender_type: "client" | "bot" | "manager" | "system" | "ai";
    text: string;
    status: "received" | "queued" | "delivering" | "accepted" | "delivery_unknown" | "retry_scheduled" | "sent" | "failed";
    created_at: string;
  } | null;
  attachments?: FileAttachment[];
  created_at: string;
  updated_at: string;
};

export type BotMessage = {
  id: Id;
  conversation: Id;
  direction: "inbound" | "outbound";
  sender_type: "client" | "bot" | "manager" | "system" | "ai";
  text: string;
  external_message_id?: string;
  payload_json: Record<string, unknown>;
  error_text?: string;
  status: "received" | "queued" | "delivering" | "accepted" | "delivery_unknown" | "retry_scheduled" | "sent" | "failed";
  delivery_attempts?: number;
  delivery_max_attempts?: number;
  delivery_next_retry_at?: string | null;
  sent_at?: string | null;
  delivered_at?: string | null;
  read_at?: string | null;
  created_at: string;
  attachments?: FileAttachment[];
};

export type Conversation = {
  id: Id;
  business: Id;
  client: Id;
  channel: "telegram" | "whatsapp" | "instagram" | "website" | "manual";
  external_chat_id: string;
  status: "open" | "closed" | "archived";
  created_at: string;
  updated_at: string;
};

export type Message = {
  id: Id;
  conversation: Id;
  sender_type: "client" | "bot" | "manager" | "system";
  text: string;
  raw_payload: Record<string, unknown>;
  created_at: string;
};

export type QuickReplyTemplate = {
  id: Id;
  business: Id;
  title: string;
  text: string;
  category: string;
  channel: "all" | "telegram" | "whatsapp" | "instagram" | "website" | "manual";
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};
