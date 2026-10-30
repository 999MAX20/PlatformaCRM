import type { Id } from "./core";

export type AuditLog = {
  id: Id;
  business: Id | null;
  business_name?: string;
  actor: Id | null;
  actor_email?: string;
  action: "create" | "update" | "delete" | "support_access";
  category: "data" | "access" | "security" | "system" | "integration";
  risk_level: "low" | "medium" | "high" | "critical";
  entity_type: string;
  entity_id: string;
  metadata: Record<string, unknown>;
  ip_address: string | null;
  user_agent: string;
  created_at: string;
};

export type LoginHistory = {
  id: Id;
  business: Id | null;
  business_name?: string;
  user: Id | null;
  user_email?: string;
  email: string;
  status: "success" | "failed";
  ip_address: string | null;
  user_agent: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type SupportAccessGrant = {
  id: Id;
  business: Id;
  user: Id;
  user_email?: string;
  reason: string;
  is_active: boolean;
  expires_at: string;
  created_at: string;
  created_by: Id | null;
  created_by_email?: string;
  is_valid_now?: boolean;
};

export type SecurityRiskSummary = {
  business: Id;
  risk_counts: Record<"low" | "medium" | "high" | "critical", number>;
  failed_logins: number;
  active_support_grants: number;
};
