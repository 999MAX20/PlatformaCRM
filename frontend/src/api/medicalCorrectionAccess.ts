import { apiClient } from "./client";
import type { ClinicalContent } from "./medicalClinical";

export type CorrectionState = "pending" | "active" | "rejected" | "withdrawn" | "completed" | "revoked" | "expired";
export type CorrectionAccess = {
  id: number; patient_id: number; encounter_id: number; document_id: number | null; requester_id: number;
  state: CorrectionState; revision: number; patient_revision: number; target_revision: number;
  created_at: string; reviewed_at: string | null; expires_at: string | null; closed_at: string | null;
  reason: string; decision_reason: string; closure_reason: string;
  encounter_started_at: string; requester_name: string; reviewed_by_name: string | null; closed_by_name: string | null;
};
export type CorrectionScope = { business_id: number; branch_id: number; client_id: number };
export type CorrectionPage = { results: CorrectionAccess[]; next_before_id: number | null; member_id: number; can_review: boolean; server_time: string };
export type CorrectionTarget = { encounter_id: number; patient_id: number; patient_revision: number; revision: number;
  state: "draft" | "finalized"; started_at: string; documents: { id: number; revision: number; created_at: string; state: string }[] };
export type CorrectionTargets = { results: CorrectionTarget[]; next_before_id: number | null };
export type CorrectionTargetContent = { access: CorrectionAccess; version_id: number; revision: number; state: string;
  content: { content?: ClinicalContent; document_text?: string; reason: string } };
const root = "/api/medical/correction-access/";
async function command(path: string, payload: object, key: string) {
  return (await apiClient.post<unknown>(path, payload, { headers: { "Idempotency-Key": key } })).data;
}
export const correctionAccessApi = {
  list: async (scope: CorrectionScope & { head?: boolean; before_id?: number }, signal?: AbortSignal) =>
    (await apiClient.get<CorrectionPage>(root, { params: scope, signal })).data,
  targets: async (scope: CorrectionScope & { before_id?: number }, signal?: AbortSignal) =>
    (await apiClient.get<CorrectionTargets>(`${root}targets/`, { params: scope, signal })).data,
  target: async (id: number, businessId: number, signal?: AbortSignal) =>
    (await apiClient.get<CorrectionTargetContent>(`${root}${id}/target/`, { params: { business_id: businessId }, signal })).data,
  request: (payload: { business_id: number; encounter_id: number; document_id?: number; expected_patient_revision: number;
    expected_target_revision: number; reason: string }, key: string) => command(root, payload, key),
  review: (id: number, payload: { business_id: number; expected_revision: number; decision: "approve" | "reject"; reason: string }, key: string) =>
    command(`${root}${id}/review/`, payload, key),
  close: (id: number, payload: { business_id: number; expected_revision: number; decision: "withdraw" | "complete" | "revoke"; reason: string }, key: string) =>
    command(`${root}${id}/close/`, payload, key),
  save: (id: number, payload: { business_id: number; expected_revision: number; reason: string; content?: ClinicalContent; document_text?: string }, key: string) =>
    command(`${root}${id}/save-draft/`, payload, key),
};
