import { apiClient } from "./client";
export type AdministrativeScope = { business_id: number; branch_id: number; client_id: number };
export type AdministrativeOption = { id: number; name: string; start_at?: string; updated_at?: string; service_name?: string };
export type AdministrativeOptions = { results: AdministrativeOption[]; next_id: number | null };
export type AdministrativeDraft = AdministrativeScope & { source_appointment_id: number; expected_updated_at: string;
  service_id: number; preferred_resource_id: number; recommended_from: string; recommended_until: string; patient_in_clinic: boolean; reason: string };
const root = "/api/reception/booking-requests/";
export const medicalReceptionAdministrationApi = {
  options: async (scope: AdministrativeScope & { kind: string; after_id?: number; search?: string }, signal?: AbortSignal) =>
    (await apiClient.get<AdministrativeOptions>(root + "administrative-options/", { params: scope, signal })).data,
  create: async (payload: AdministrativeDraft, key: string) =>
    (await apiClient.post<{ id: number; replayed: boolean }>(root + "administrative/", payload, { headers: { "Idempotency-Key": key } })).data,
};
