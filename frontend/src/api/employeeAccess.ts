import { apiClient } from "./client";

export type AccessAction = "disable" | "restore" | "role" | "reissue" | "revoke";
export type AccessRepair = {
  id: string; business_id: number; business_name: string; target_id: number; target_name: string; target_email: string;
  action: AccessAction; status: string; reason: string; target_role: { id: number; name: string } | null; target_role_key: string;
  owner_required: boolean; owner_confirmed_at: string | null; expires_at: string; completed_at: string | null;
  support_case_id: number; prepared_by: string; executed_by: string | null;
};
export type AccessMember = {
  id: number; user_id: number; name: string; email: string; account_active: boolean; membership_active: boolean;
  role: string; business_role: { id: number; name: string; active: boolean } | null; protected: boolean; revision: string;
  specialists: { id: number; name: string; is_active: boolean; retired_at: string | null; appointments: number }[];
  dependencies: Record<"tasks" | "leads" | "deals" | "conversations", number>;
};
export type AccessInvitation = { id: number; name: string; email: string; role: string; status: string; expires_at: string; revision: string; protected: boolean };
export type AccessSnapshot = { members: AccessMember[]; invitations: AccessInvitation[]; members_count: number; invitations_count: number;
  page: number; page_size: number; roles: { id: number; name: string }[]; requests: AccessRepair[] };
export type AccessTerms = { request_id: string; action: AccessAction; target_id: number; target_role_id: number | null;
  expected_revision: string; support_case_id: number; reason: string };
const root = (business: string) => `/api/platform/merchants/${business}/employee-access/`;
const mfa = (token: string) => ({ headers: { "X-Zani-MFA-Step-Up": token } });
export const employeeAccessApi = {
  get: async (business: string, params: { search: string; page: number }) => (await apiClient.get<AccessSnapshot>(root(business), { params })).data,
  prepare: async (business: string, data: AccessTerms, token: string) => (await apiClient.post<AccessRepair>(root(business), data, mfa(token))).data,
  act: async (business: string, id: string, action: "execute" | "cancel", token: string) => (await apiClient.post<AccessRepair>(`${root(business)}${id}/`, { action }, mfa(token))).data,
  mine: async () => (await apiClient.get<{ results: AccessRepair[] }>("/api/auth/employee-access-confirmations/")).data.results,
  decide: async (id: string, decision: "confirm" | "decline") => (await apiClient.post<AccessRepair>(`/api/auth/employee-access-confirmations/${id}/`, { decision })).data,
};
