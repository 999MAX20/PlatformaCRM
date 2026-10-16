import axios from "axios";
import { apiClient } from "./client";

export type RecoveryRequest = {
  id: string; business_id: number; business_name: string; user_id: number; user_name: string;
  new_email: string; status: string; owner_required: boolean; owner_confirmed_at: string | null;
  identity_required?: boolean; verified_reference?: string; reason?: string;
  delivery_status: string; last_attempt_at: string | null; expires_at: string;
  completed_at: string | null; support_case_id: number;
};
export type RecoveryCandidate = {
  id: number; name: string; email: string; revision: string; owner_required: boolean;
  identity_required: boolean; mfa_enabled: boolean; email_change_status: string;
  email_change_expires_at: string | null;
};
export type RecoverySnapshot = { candidates: RecoveryCandidate[]; requests: RecoveryRequest[] };
export type RecoveryTerms = {
  user_id: number; support_case_id: number; new_email: string; expected_revision: string;
  reason: string; verified_reference: string;
};
const root = (business: string) => `/api/platform/merchants/${business}/account-recovery/`;
const mfa = (token: string) => ({ headers: { "X-Zani-MFA-Step-Up": token } });
const publicClient = axios.create({ baseURL: import.meta.env.VITE_API_URL || "", timeout: 20_000 });
export const recoveryApi = {
  get: async (business: string) => (await apiClient.get<RecoverySnapshot>(root(business))).data,
  prepare: async (business: string, terms: RecoveryTerms, token: string) => (await apiClient.post<RecoveryRequest>(root(business), terms, mfa(token))).data,
  act: async (business: string, id: string, action: "send" | "cancel", token: string) => (await apiClient.post<RecoveryRequest>(`${root(business)}${id}/`, { action }, mfa(token))).data,
  mine: async () => (await apiClient.get<{ results: RecoveryRequest[] }>("/api/auth/recovery-confirmations/")).data.results,
  decide: async (id: string, decision: "confirm" | "decline") => (await apiClient.post<RecoveryRequest>(`/api/auth/recovery-confirmations/${id}/`, { decision })).data,
  contact: async () => (await publicClient.get<{ support_email: string | null }>("/api/auth/account-recovery/")).data,
  complete: async (recovery_id: string, token: string, password: string) => (await publicClient.post<{ ok: boolean }>("/api/auth/account-recovery/", { recovery_id, token, password })).data,
};
