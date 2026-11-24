import { apiClient } from "./client";

export type Duty = { revision: number; lead_id: number; deputy_id: number | null; lead_available: boolean; starts_at: string; ends_at: string };
export type DutyWrite = Omit<Duty, "revision"> & { business_id: number; branch_id: number; expected_revision: number; reason: string };
export type DutyOptions = { results: { id: number; name: string }[]; next_id: number | null; duty?: Duty | null };
const path = "/api/medical/role-management/reception-duty/";
export const medicalReceptionDutyApi = {
  read: async (scope: { business_id: number; branch_id?: number; kind?: string; after_id?: number; search?: string }, signal?: AbortSignal) =>
    (await apiClient.get<DutyOptions>(path, { params: scope, signal })).data,
  save: async (payload: DutyWrite, key: string) =>
    (await apiClient.post(path, payload, { headers: { "Idempotency-Key": key } })).data,
};
