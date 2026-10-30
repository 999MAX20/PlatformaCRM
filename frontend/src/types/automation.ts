import type { Id } from "./core";

export type AutomationRule = {
  id: Id;
  business: Id;
  name: string;
  trigger_type: string;
  description: string;
  is_active: boolean;
  priority: number;
  conditions?: Array<Record<string, unknown>>;
  actions?: Array<Record<string, unknown>>;
  created_at: string;
  updated_at: string;
};

export type AutomationTemplate = {
  key: string;
  name: string;
  description: string;
  trigger_type: string;
  actions: Array<Record<string, unknown>>;
  conditions?: Array<Record<string, unknown>>;
};

export type AutomationRun = {
  id: Id;
  business: Id;
  rule: Id | null;
  rule_name?: string;
  trigger_type: string;
  entity_type: string;
  entity_id: string;
  idempotency_key?: string | null;
  status: "pending" | "running" | "waiting" | "retry_scheduled" | "success" | "failed" | "skipped" | "cancelled";
  payload: Record<string, unknown>;
  action_results?: Array<Record<string, unknown>>;
  error: string;
  attempts?: number;
  max_attempts?: number;
  run_after?: string | null;
  next_retry_at?: string | null;
  locked_at?: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
};

export type AutomationConditionDraft = {
  field: string;
  operator: "eq" | "gt" | "lt" | "contains" | "in";
  value: unknown;
};

export type AutomationActionDraft = {
  action_type: "create_task" | "create_notification" | "assign_user" | "add_note" | "create_follow_up" | "wait";
  config: Record<string, unknown>;
  delay_seconds: number;
};

export type ManualAutomationRulePayload = {
  business: Id;
  name: string;
  trigger_type: string;
  description?: string;
  is_active?: boolean;
  priority?: number;
  conditions: AutomationConditionDraft[];
  actions: AutomationActionDraft[];
};

export type AutomationPreview = {
  valid: boolean;
  name: string;
  trigger_type: string;
  trigger_label: string;
  conditions_count: number;
  actions_count: number;
  will_run_when: string;
  steps: AutomationActionDraft[];
};
