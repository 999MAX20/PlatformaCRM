import type { Id } from "./core";

export type SubscriptionPlan = {
  id: Id;
  name: string;
  code: string;
  monthly_price: string;
  description: string;
  is_active: boolean;
  limits_json: Record<string, unknown>;
  features_json: { features?: string[] } & Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type Subscription = {
  id: Id;
  business: Id;
  plan?: SubscriptionPlan | null;
  status: "trial" | "active" | "overdue" | "cancelled" | "paused";
  billing_email: string;
  payment_method: string;
  invoice_details_json: Record<string, unknown>;
  requested_plan?: Id | null;
  requested_plan_name?: string | null;
  plan_change_requested_at?: string | null;
  started_at: string | null;
  next_payment_at: string | null;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
};

export type UsageSummaryItem = {
  metric: "ai_requests" | "bot_messages" | "users" | "conversations" | "storage_mb";
  value: number;
  value_bytes?: number;
  limit: number | null;
  limit_bytes?: number | null;
  is_limited: boolean;
  is_over_limit: boolean;
  period_kind?: "month" | "current";
  period_start?: string | null;
  period_end?: string | null;
};

export type EntitlementSummaryItem = {
  metric: "ai_requests" | "bot_messages" | "users" | "conversations" | "storage_mb" | "bots" | "automations";
  value: number;
  limit: number | null;
  remaining: number | null;
  is_limited: boolean;
  is_over_limit: boolean;
  plan_code: string | null;
  period_kind?: "month" | "current";
  period_start?: string | null;
  period_end?: string | null;
  unit?: "MiB" | "count";
};
