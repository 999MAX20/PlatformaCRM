import type { Id } from "./core";
import type { Business } from "./business";

export type User = {
  id: Id;
  email: string;
  full_name?: string;
  phone?: string;
  role?: "platform_admin" | "platform_manager" | "business_owner" | "business_manager" | "business_operator" | "manager" | "admin" | "operator" | "specialist" | "marketer" | "accountant" | "support" | "staff" | "doctor";
  is_platform_user?: boolean;
  is_merchant_user?: boolean;
  is_business_manager?: boolean;
};

export type CurrentUser = User & {
  businesses: Business[];
  memberships?: BusinessMembershipSummary[];
  effective_permissions?: Record<string, EffectivePermission[]>;
  capabilities?: Record<string, BusinessCapabilitySummary>;
  preferences?: UserPreference;
  social_identities?: SocialIdentitySummary[];
  is_platform_user: boolean;
  is_merchant_user: boolean;
  is_business_manager: boolean;
};

export type UserPreference = {
  language: "ru" | "kk" | "en";
  timezone: string;
  start_page: "dashboard" | "conversations" | "tasks" | "calendar" | "leads";
  created_at?: string;
  updated_at?: string;
};

export type SocialIdentitySummary = {
  provider: "google" | "apple";
  email: string;
  email_verified: boolean;
  created_at: string;
  updated_at: string;
};

export type EffectivePermission = {
  resource: string;
  action: string;
  scope: "none" | "own" | "team" | "business";
};

export type BusinessMembershipSummary = {
  business: Id;
  role: "owner" | "admin" | "manager" | "operator" | "specialist" | "marketer" | "accountant" | "support" | "staff" | "doctor";
  business_role: Id | null;
  business_role_name: string;
  is_active: boolean;
};

export type BusinessCapabilitySummary = {
  business: Id;
  business_type: Business["business_type"];
  workflow_mode: "appointment_first" | "standard_crm" | string;
  modules: Record<
    | "inbox"
    | "leads"
    | "clients"
    | "appointments"
    | "tasks"
    | "deals"
    | "analytics"
    | "ai"
    | "automations"
    | "integrations"
    | string,
    boolean
  >;
};

export type BusinessRole = {
  id: Id;
  business: Id;
  name: string;
  preset_key: string;
  description: string;
  permissions_json: Record<string, unknown>;
  is_system: boolean;
  is_active: boolean;
  permissions: RolePermission[];
  created_at: string;
  updated_at: string;
};

export type RolePermission = {
  id: Id;
  business_role: Id;
  resource: string;
  action: string;
  scope: "none" | "own" | "team" | "business";
  is_allowed: boolean;
  created_at: string;
  updated_at: string;
};

export type TeamDepartment = {
  id: Id;
  business: Id;
  name: string;
  description: string;
  is_active: boolean;
  members_count?: number;
  created_at: string;
  updated_at: string;
};

export type TeamMember = {
  branch_access?: { all_branches: boolean; branch_ids: Id[] };
  id: Id;
  business: Id;
  user: User;
  role: BusinessMembershipSummary["role"];
  business_role: Id | null;
  business_role_name?: string;
  teams?: { id: Id; name: string; is_lead: boolean }[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type BusinessInvitation = {
  id: Id;
  business: Id;
  business_name?: string;
  email: string;
  phone: string;
  telegram: string;
  full_name: string;
  role: BusinessMembershipSummary["role"];
  business_role: Id | null;
  business_role_name?: string | null;
  invited_by: Id | null;
  invited_by_email?: string | null;
  delivery_channel: "email" | "whatsapp" | "telegram" | "manual";
  token: string;
  invite_path: string;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  status: "pending" | "accepted" | "revoked" | "expired";
  created_at: string;
  updated_at: string;
};
