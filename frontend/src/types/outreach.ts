import type { Id } from "./core";

export type OutreachTemplate = {
  id: Id;
  business: Id;
  name: string;
  channel: "telegram" | "whatsapp";
  body: string;
  external_template_name: string;
  language_code: string;
  is_approved: boolean;
  is_active: boolean;
  created_by: Id | null;
  created_at: string;
  updated_at: string;
};

export type OutreachCampaign = {
  id: Id;
  business: Id;
  name: string;
  channel: "telegram" | "whatsapp";
  status: "draft" | "ready" | "scheduled" | "running" | "sent" | "cancelled";
  campaign_type: "service" | "marketing" | "transactional";
  audience_type: "all_clients" | "segment" | "manual";
  segment: Id | null;
  template: Id | null;
  message_text: string;
  require_opt_in: boolean;
  whatsapp_template_name: string;
  whatsapp_template_language: string;
  whatsapp_template_status: "not_required" | "draft" | "pending" | "approved" | "rejected";
  rate_limit_per_minute: number;
  batch_size: number;
  scheduled_at: string | null;
  created_by: Id | null;
  started_at: string | null;
  finished_at: string | null;
  recipients_total?: number;
  recipients_pending?: number;
  recipients_sent?: number;
  recipients_failed?: number;
  recipients_skipped?: number;
  created_at: string;
  updated_at: string;
};
