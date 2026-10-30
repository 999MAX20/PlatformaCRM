import type { Id } from "./core";

export type AgentProfile = {
  id: Id;
  business: Id;
  bot: Id | null;
  bot_name?: string | null;
  name: string;
  role_description: string;
  tone: "friendly" | "expert" | "formal" | "sales" | "support";
  language: string;
  is_active: boolean;
  system_prompt: string;
  rules_json: Record<string, unknown>;
  allowed_tools_json: Record<string, unknown>;
  escalation_rules_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type BusinessKnowledgeItem = {
  customer_visible?: boolean;
  id: Id;
  business: Id;
  bot: Id | null;
  title: string;
  content: string;
  category: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type AIToolCallLog = {
  id: Id;
  business: Id;
  user: Id | null;
  conversation: Id | null;
  tool_name: string;
  input_json: Record<string, unknown>;
  output_json: Record<string, unknown>;
  status: "suggested" | "executing" | "executed" | "failed" | "rejected";
  error: string;
  attempts?: number;
  executed_at?: string | null;
  created_at: string;
};

export type ApprovalRequest = {
  id: Id;
  business: Id;
  requested_by: Id | null;
  action_type:
    | "ai_pipeline"
    | "ai_outreach"
    | "ai_automation"
    | "campaign_launch"
    | "appointment_change"
    | "export";
  payload: Record<string, unknown>;
  source_object_type: string;
  source_object_id: string;
  ai_tool_call_log: Id | null;
  status: "pending" | "approved" | "rejected" | "expired" | "executed";
  reason: string;
  created_at: string;
  updated_at: string;
};

export type AIToolDefinition = {
  name: string;
  description: string;
  requires_confirmation: boolean;
};

export type AIToolSuggestResponse = {
  tools: AIToolDefinition[];
  suggested_actions: AIToolCallLog[];
};
