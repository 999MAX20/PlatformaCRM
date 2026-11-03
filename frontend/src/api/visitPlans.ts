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
};
export type PlanResult = VisitPlan | { read_restricted: true };
export type PlanHistoryEvent = { id: number; created_at: string; command: string; actor_name: string };
export const visitPlansApi = {
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
