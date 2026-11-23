import { apiClient } from "./client";

export type ActualVisitScope = { business_id: number; client_id: number; branch_id: number };
export type ActualVisitContext = { patient_id: number; patient_revision: number; earlier_allowed: boolean; resource_ids: number[]; now: string };
export type ActualVisitResult = { id: number; start_at: string; replayed: boolean };
export type ActualVisitRequest = ActualVisitScope & { service_id: number; resource_id: number; start_at: string;
  expected_patient_revision: number; expected_price: string | null; expected_duration_minutes: number; reason: string };
const root = "/api/medical/encounters/";
export const medicalActualVisitsApi = {
  async context(scope: ActualVisitScope, signal?: AbortSignal): Promise<ActualVisitContext> {
    return (await apiClient.get(`${root}actual-context/`, { params: scope, signal })).data;
  },
  async create(payload: ActualVisitRequest, key: string, signal?: AbortSignal): Promise<ActualVisitResult> {
    return (await apiClient.post(`${root}actual-visit/`, payload, { headers: { "Idempotency-Key": key }, signal })).data;
  },
};
