import { apiClient, type PaginatedResponse } from "./client";

export type PlanStepInput = { service: number; resource?: number | null; branch?: number | null; responsible_user?: number | null };
export type PlanStep = PlanStepInput & {
  id: number; service_name: string; resource_name: string; appointment: number | null;
  start_at: string | null; status: string; removed_at: string | null;
};
export type VisitPlan = {
  id: number; business: number; client: number; client_name: string; revision: number;
  responsible_user: number; responsible_user_name: string; is_archived: boolean;
  can_change: boolean; steps: PlanStep[];
  money: PlanMoney | null;
};
export type PlanTerms = { id: number; revision: number; mode: "package" | "per_visit"; currency: string; total: string;
  lines: { step: number; base: string; amount: string; frozen: boolean }[]; reason: string; created_at: string };
export type PlanMoney = { terms: PlanTerms | null; terms_current: boolean; received: string; allocated: string;
  refunded: string; unallocated: string; retained: string; remaining: string; incoming_credit: string; outgoing_credit: string;
  can_receive: boolean; can_manage: boolean;
  sources: { id: number; amount: string; available: string; retained: string; method: string; occurred_at: string }[];
  allocations: { id: number; appointment: number; amount: string; reversal_of: number | null; created_at: string }[] };
export type PlanTermsDraft = { expected_revision: number; mode: "package" | "per_visit"; total: string;
  base_prices: { step: number; amount: string }[]; reason: string; consent: boolean; preview_hash?: string };
export type PlanTermsPreview = Pick<PlanTerms, "mode" | "currency" | "total" | "lines"> & { preview_hash: string;
  balance: Pick<PlanMoney, "received" | "refunded" | "allocated" | "unallocated" | "retained"> };
export type PlanCreditOption = { source_plan: number; source_revision: number; receipt: number; amount: string; currency: string };
export type PlanResult = VisitPlan | { read_restricted: true };
export type PlanHistoryEvent = { id: number; created_at: string; command: string; actor_name: string };
export const visitPlansApi = {
  termsHistory: async (business: number, id: number, page: number) =>
    (await apiClient.get<PaginatedResponse<PlanTerms & { actor_name: string }>>(`/api/visit-plans/${id}/terms-history/`, { params: { business, page } })).data,
  creditOptions: async (business: number, id: number, page: number) =>
    (await apiClient.get<PaginatedResponse<PlanCreditOption>>(`/api/visit-plans/${id}/credit-options/`, { params: { business, page } })).data,
  previewTerms: async (business: number, id: number, payload: PlanTermsDraft) =>
    (await apiClient.post<PlanTermsPreview>(`/api/visit-plans/${id}/preview-terms/`, payload, { params: { business } })).data,
  history: async (business: number, id: number, page: number) =>
    (await apiClient.get<PaginatedResponse<PlanHistoryEvent>>(`/api/visit-plans/${id}/history/`, { params: { business, page } })).data,
  list: async (params: { business: number; client?: number; page: number; archived: boolean }) =>
    (await apiClient.get<PaginatedResponse<VisitPlan>>("/api/visit-plans/", { params })).data,
  get: async (business: number, id: number) =>
    (await apiClient.get<VisitPlan>(`/api/visit-plans/${id}/`, { params: { business } })).data,
  create: async (payload: { business: number; client: number; responsible_user?: number; steps: PlanStepInput[] }, key: string) =>
    (await apiClient.post<PlanResult>("/api/visit-plans/", payload, { headers: { "Idempotency-Key": key } })).data,
  command: async (business: number, id: number, command: string, payload: Record<string, unknown>, key: string) =>
    (await apiClient.post<PlanResult>(`/api/visit-plans/${id}/commands/${command}/`, payload,
      { params: { business }, headers: { "Idempotency-Key": key } })).data,
};
