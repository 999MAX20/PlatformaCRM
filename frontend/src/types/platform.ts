import type { Id } from "./core";
import type { Business } from "./business";
import type { User } from "./identity";
import type { SubscriptionPlan, Subscription, UsageSummaryItem } from "./billing";

export type PlatformOperationsSummary = {
  total_monitored: number;
  attention_merchants: number | null;
  risk_merchants: number;
  no_sales_data_merchants: number | null;
  form_error_merchants: number | null;
  handoff_conversations: number | null;
  new_leads_30d: number | null;
  form_errors_30d: number | null;
  failed_connectors: number | null;
  unavailable_sources?: string[];
};

export type PlatformMerchantOperations = {
  lead_count: number | null;
  new_leads: number | null;
  clients_count: number | null;
  open_tasks: number | null;
  unread_conversations: number | null;
  handoff_conversations: number | null;
  failed_connectors: number | null;
  pending_connectors?: number | null;
  connected_connectors: number | null;
  form_errors: number | null;
  lead_forms: number | null;
  sales_events: number | null;
  latest_activity_at: string | null;
  unavailable_sources?: string[];
};

export type PlatformMerchantHealth = {
  score: number | null;
  status: "healthy" | "setup" | "attention" | "risk" | string;
  checks: Record<string, boolean | null>;
  blockers: string[];
  next_action: string;
};

export type PlatformSupportAction = {
  id: Id;
  action_type: string;
  note: string;
  status: string;
  created_at: string;
  actor_email: string | null;
};

export type PlatformSupportStep = {
  key: string;
  label: string;
  href: string;
};

export type PlatformSupportWorkflow = {
  priority: "low" | "medium" | "high" | string;
  summary: string;
  next_steps: PlatformSupportStep[];
  recent_actions: PlatformSupportAction[];
};

export type PlatformOverview = {
  attention: import("./platformOverview").OverviewAttention;
  generated_at?: string;
  service_status?: PlatformOperationsHealth["service_status"];
  total_businesses: number;
  active_businesses: number;
  trial_businesses: number;
  active_subscriptions: number | null;
  mrr_estimate: string | null;
  total_users: number;
  bot_count: number | null;
  active_bot_channels: number | null;
  ai_requests_30d: number | null;
  conversations_30d: number | null;
  operations_summary: PlatformOperationsSummary;
  errors: {
    count: number | null;
    items: unknown[];
  };
};

export type PlatformHealthGate = {
  key: string;
  title?: string;
  status: "pass" | "warn" | "fail" | string;
  severity?: string;
  detail: string;
  action: string;
};

export type PlatformProviderRolloutCheck = {
  provider: string;
  title: string;
  order: number;
  enabled: boolean;
  status: "ready" | "warning" | "blocked" | string;
  gates: PlatformHealthGate[];
};

export type PlatformOperationsHealth = {
  unavailable_sources?: string[];
  service_status?: {
    scope: string;
    status: "healthy" | "degraded" | "unknown";
    businesses: { total: number; healthy: number; degraded: number; unknown: number } | null;
    max_age_seconds?: number;
    incidents?: Array<{ business_id: Id; component: string; episode: number; started_at: string; observed_at: string; affected_count: number }>;
  };
  environment: string;
  release: string;
  generated_at: string;
  status: "healthy" | "warning" | "critical" | string;
  summary: {
    critical: number;
    warning: number;
    active_support_grants: number | null;
    connector_requests: number | null;
  };
  runtime: {
    queue: {
      broker_configured: boolean;
      automation_inline: boolean;
      default_queue: string;
      queues: string[];
      status: "healthy" | "warning" | "critical" | string;
      automation_runs: {
        pending: number | null;
        running: number | null;
        failed: number | null;
      };
      failed_connector_syncs: number | null;
      failed_webhook_deliveries: number | null;
    };
    production_readiness: {
      summary: Record<string, number>;
      failed_items: PlatformHealthGate[];
      warning_items: PlatformHealthGate[];
    };
    backup_readiness: {
      summary: Record<string, number>;
      failed_items: PlatformHealthGate[];
    };
    provider_rollout: {
      summary: Record<string, number>;
      providers: PlatformProviderRolloutCheck[];
    };
  };
  work_queue: {
    connector_requests: Array<{
      id: Id;
      business_id: Id;
      business_name: string;
      provider: string;
      name: string;
      status: string;
      last_error: string;
      updated_at: string;
      created_by_email: string | null;
    }>;
    failed_automation_runs: Array<{
      id: Id;
      business_id: Id;
      business_name: string;
      trigger_type: string;
      entity_type: string;
      entity_id: string;
      status: string;
      attempts: number;
      max_attempts: number;
      error: string;
      created_at: string;
    }>;
    failed_integration_events: Array<{
      id: Id;
      business_id: Id | null;
      business_name: string;
      provider: string;
      channel: string;
      direction: string;
      status: string;
      error: string;
      created_at: string;
    }>;
    failed_webhook_deliveries: Array<{
      id: Id;
      business_id: Id;
      business_name: string;
      endpoint_name: string;
      event_type: string;
      status: string;
      attempts: number;
      error: string;
      created_at: string;
    }>;
  };
};

export type PlatformMerchant = {
  timezone?: string;
  id: Id;
  name: string;
  status: Business["status"];
  created_at?: string;
  latest_activity_at?: string | null;
  generated_at?: string;
  service_status?: PlatformClinicService;
  landing_id?: string;
  landing_domain?: string;
  owner: Pick<User, "id" | "email" | "full_name">;
  plan: Pick<SubscriptionPlan, "id" | "name" | "code" | "monthly_price"> | null;
  subscription_status: Subscription["status"] | null;
  usage_summary: UsageSummaryItem[];
  operations?: PlatformMerchantOperations;
  health?: PlatformMerchantHealth;
  support_workflow?: PlatformSupportWorkflow;
  can_log_support_action?: boolean;
};

export type PlatformClinicService = {
  status: "healthy" | "degraded" | "unknown";
  checked_at?: string;
  max_age_seconds?: number;
  source_available?: boolean;
  components: Array<{
    component: string;
    state: "healthy" | "degraded" | "unknown";
    last_state: string | null;
    observed_at: string | null;
    episode: number;
    started_at: string | null;
    recovered_at: string | null;
  }>;
};
