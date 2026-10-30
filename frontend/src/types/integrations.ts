import type { Id } from "./core";

export type Bot = {
  scenario?: "inbox" | "crm";
  id: Id;
  business: Id;
  name: string;
  status: "draft" | "active" | "paused";
  default_language: string;
  settings_json: Record<string, unknown>;
  readiness?: {
    is_ready: boolean;
    profile_ready: boolean;
    channel_ready: boolean;
    knowledge_ready: boolean;
    missing: Array<"profile" | "channel" | "knowledge">;
  };
  created_at: string;
  updated_at: string;
};

export type BotChannel = {
  id: Id;
  bot: Id;
  channel: "website" | "telegram" | "whatsapp" | "instagram";
  status: "draft" | "active" | "paused" | "error";
  external_id: string;
  public_token: string;
  config_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type IntegrationEventLog = {
  id: Id;
  business: Id | null;
  business_name?: string | null;
  provider: "website" | "telegram" | "whatsapp" | "instagram" | "email" | string;
  channel: string;
  direction: "inbound" | "outbound";
  payload_json: Record<string, unknown>;
  status: "received" | "processed" | "sent" | "mocked" | "failed";
  error: string;
  created_at: string;
};

export type ApiToken = {
  id: Id;
  business: Id;
  name: string;
  token_prefix: string;
  scopes_json: string[];
  is_active: boolean;
  expires_at: string | null;
  last_used_at: string | null;
  created_by: Id | null;
  created_by_email?: string | null;
  created_at: string;
  updated_at: string;
};

export type ApiTokenCreateResponse = ApiToken & {
  token: string;
};

export type WebhookEndpoint = {
  id: Id;
  business: Id;
  name: string;
  url: string;
  events_json: string[];
  is_active: boolean;
  created_by: Id | null;
  created_by_email?: string | null;
  created_at: string;
  updated_at: string;
};

export type WebhookDeliveryLog = {
  id: Id;
  business: Id;
  endpoint: Id;
  endpoint_name?: string;
  event_type: string;
  idempotency_key: string;
  payload_json: Record<string, unknown>;
  response_status: number | null;
  response_body: string;
  status: "pending" | "sent" | "failed";
  error: string;
  attempts: number;
  next_retry_at: string | null;
  delivered_at: string | null;
  created_at: string;
};

export type BusinessConnector = {
  id: Id;
  business: Id;
  business_name?: string;
  provider: "website" | "telegram" | "whatsapp" | "instagram" | "email" | "kaspi" | "1c" | "google_calendar" | "excel_csv" | "google_sheets" | "moysklad" | "wildberries" | "ozon" | "yandex_market" | "custom" | string;
  capability: "communications" | "sales" | "calendar" | "finance" | "inventory" | "marketing" | "custom" | string;
  name: string;
  status: "draft" | "connected" | "pending_request" | "setup_required" | "provider_configuring" | "error" | "disconnected" | "needs_attention" | "syncing" | "failed" | "disabled" | "expired_credentials";
  auth_type: "none" | "token" | "oauth" | "qr" | "login" | "connector";
  config_json: Record<string, unknown>;
  scopes_json: string[];
  last_sync_at: string | null;
  next_sync_at: string | null;
  last_error: string;
  connected_at: string | null;
  created_by: Id | null;
  created_by_email?: string | null;
  credentials_count?: number;
  created_at: string;
  updated_at: string;
};

export type ConnectorCapability = {
  provider: BusinessConnector["provider"];
  label: string;
  capability: BusinessConnector["capability"];
  auth_type: BusinessConnector["auth_type"];
  description: string;
  launch_status: "available" | "beta" | "soon" | "request" | "roadmap" | string;
  cta_label: string;
  next_step: string;
  pilot_note: string;
  setup_priority: number;
  is_pilot_safe: boolean;
  availability: "included" | "upgrade" | "request" | "soon" | "roadmap" | string;
  required_plan: "basic" | "business" | "pro" | string;
  setup_state: "active" | "setup_required" | "request_required" | "coming_soon" | "roadmap" | string;
  action_behavior: "self_service" | "request" | "disabled" | string;
  primary_action_label: string;
};

export type ConnectorCredential = {
  id: Id;
  business: Id;
  connector: Id;
  connector_name?: string;
  provider?: string;
  key: string;
  masked_value: string;
  expires_at: string | null;
  rotated_at: string | null;
  created_at: string;
  updated_at: string;
};

export type BusinessEvent = {
  id: Id;
  business: Id;
  connector: Id | null;
  connector_name?: string | null;
  event_type: string;
  source: string;
  external_id: string;
  deduplication_key: string;
  occurred_at: string;
  processed_at: string | null;
  payload_json: Record<string, unknown>;
  status: "received" | "processed" | "failed" | "ignored";
  error: string;
  created_at: string;
};

export type ConnectorSyncRun = {
  id: Id;
  business: Id;
  connector: Id;
  connector_name?: string;
  mode: "webhook" | "pull" | "manual" | "healthcheck";
  status: "queued" | "running" | "succeeded" | "failed";
  started_at: string | null;
  finished_at: string | null;
  events_received: number;
  events_processed: number;
  error: string;
  created_at: string;
};
