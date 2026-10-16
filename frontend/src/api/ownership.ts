import { apiClient } from "./client";

type Person = { id: number; name: string; email: string };
export type OwnershipTransfer = {
  id: string; business: { id: number; name: string; timezone: string }; previous_owner: Person; new_owner: Person;
  previous_owner_role: string; previous_owner_business_role: { id: number; name: string } | null;
  reason: string; support_case_id: number; status: "pending" | "completed" | "cancelled" | "expired";
  previous_owner_confirmed_at: string | null; new_owner_confirmed_at: string | null;
  expires_at: string; completed_at: string | null;
  actions: { confirm: boolean; decline: boolean; cancel: boolean; execute: boolean };
};
export type OwnershipSnapshot = {
  owner: Person; can_prepare: boolean; candidates: Person[];
  employee_roles: { id: number; name: string }[]; transfers: OwnershipTransfer[];
};
export type OwnershipTerms = {
  new_owner_id: number; expected_owner_id: number; previous_owner_business_role_id: number | null;
  support_case_id: number; reason: string;
};
const root = (business: string) => `/api/platform/merchants/${business}/ownership/`;
const mfa = (token: string) => ({ headers: { "X-Zani-MFA-Step-Up": token } });
export const ownershipApi = {
  get: async (business: string) => (await apiClient.get<OwnershipSnapshot>(root(business))).data,
  prepare: async (business: string, terms: OwnershipTerms, token: string) =>
    (await apiClient.post<OwnershipTransfer>(root(business), terms, mfa(token))).data,
  act: async (business: string, id: string, action: "execute" | "cancel", token: string) =>
    (await apiClient.post<OwnershipTransfer>(`${root(business)}${id}/`, { action }, mfa(token))).data,
  mine: async () => (await apiClient.get<{ results: OwnershipTransfer[] }>("/api/auth/ownership-transfers/")).data.results,
  decide: async (id: string, decision: "confirm" | "decline") =>
    (await apiClient.post<OwnershipTransfer>(`/api/auth/ownership-transfers/${id}/decision/`, { decision })).data,
};
