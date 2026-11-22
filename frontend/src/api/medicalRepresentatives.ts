import { apiClient } from "./client";
import type { PatientProtocolLabel, PatientScope, PatientVerificationForm } from "./medicalPatients";

export type Representative = {
  id: number; representative_client_id: number; full_name: string; revision: number;
  permissions: string[]; permission_labels: Record<string, PatientProtocolLabel> | null;
  status: "active" | "scheduled" | "expired" | "revoked";
  valid_from: string; valid_until: string | null; verified_at: string; revoked_at: string | null;
};
export type RepresentativeForm = PatientVerificationForm & {
  requires_expiry: boolean; permissions: Array<{ code: string; label: PatientProtocolLabel }>;
};
export type RepresentativeCreate = PatientScope & {
  representative_client_id: number; expected_patient_revision: number; expected_client_updated_at: string;
  protocol_reference: string; method: string; fields: Record<string, string>; permissions: string[];
  valid_from: string; valid_until: string | null;
};
export type RepresentativeRevoke = PatientScope & { representative_client_id: number; expected_revision: number; reason: string };
type Result = { id: number; revision: number; replayed: boolean };
const root = "/api/medical/patients/";
async function command(path: string, payload: RepresentativeCreate | RepresentativeRevoke, key: string, signal?: AbortSignal) {
  if (!key.trim()) throw new Error("Representative command requires an idempotency key.");
  return (await apiClient.post<Result>(root + path, payload, { headers: { "Idempotency-Key": key }, signal })).data;
}
export const medicalRepresentativesApi = {
  list: async (patientId: number, scope: PatientScope, offset = 0, signal?: AbortSignal) =>
    (await apiClient.get<{ results: Representative[]; next_offset: number | null }>(`${root}${patientId}/representatives/`, { params: { ...scope, offset }, signal })).data,
  form: async (scope: PatientScope, signal?: AbortSignal) =>
    (await apiClient.get<RepresentativeForm>(root + "representative-form/", { params: scope, signal })).data,
  verify: (patientId: number, payload: RepresentativeCreate, key: string, signal?: AbortSignal) =>
    command(`${patientId}/representatives/`, payload, key, signal),
  revoke: (patientId: number, id: number, payload: RepresentativeRevoke, key: string, signal?: AbortSignal) =>
    command(`${patientId}/representatives/${id}/revoke/`, payload, key, signal),
};
