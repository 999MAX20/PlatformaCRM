import { apiClient } from "./client";
import type { DocumentDraft, DocumentPreview, DocumentVersion } from "./medicalDocuments";

export type AssistantState = "pending" | "active" | "declined" | "revoked" | "ended";
export type AssistantPage<T> = { results: T[]; next_before_id: number | null };
export type AssistantPageScope = { business_id: number; before_id?: number; limit?: number };
export type AssistantManagementScope = AssistantPageScope & { patient_id: number; appointment_id: number };
export type AssistantCommandResult = { id: number; state: AssistantState; revision: number; replayed: boolean };
export type AssistantAssignment = {
  id: number; member_id: number; name: string; state: AssistantState; revision: number;
  invited_at: string; accepted_at: string | null; closed_at: string | null; inviter_name: string;
};
export type AssistantInvitation = {
  id: number; state: AssistantState; revision: number; branch_name: string;
  clinician_name: string; inviter_name: string; start_at: string; invited_at: string;
  can_accept: boolean; can_open: boolean;
};
export type AssistantWorkspace = {
  invitation_id: number; business_id: number; patient_id: number; patient_name: string; patient_revision: number;
  appointment_id: number; start_at: string; branch_name: string; clinician_name: string;
  encounter_id: number | null; encounter_revision: number | null; actions: { create: boolean; update: boolean };
};
export type AssistantDraftRow = {
  id: number; version_id: number; revision: number; title: string; created_at: string;
  prepared_by: DocumentVersion["snapshot"]["prepared_by"]; state: "draft";
};
export type AssistantTemplateRow = { template_id: number; version_id: number; revision: number; title: string };
export type AssistantDocumentScope = { business_id: number; patient_id: number; encounter_id: number };
export type AssistantDocumentDraft = Omit<DocumentDraft, "participation_id"> & {
  document_id?: number; expected_document_revision?: number;
};

const root = "/api/medical/appointment-assistants/";
async function read<T>(path: string, params: object, signal?: AbortSignal) {
  return (await apiClient.get<T>(root + path, { params, signal })).data;
}
async function command<T>(path: string, payload: object, key: string, signal?: AbortSignal) {
  if (!key.trim() || key.length > 128) throw new Error("Medical command requires an idempotency key of at most 128 characters.");
  return (await apiClient.post<T>(root + path, payload, { headers: { "Idempotency-Key": key }, signal })).data;
}

export const medicalAssistantsApi = {
  candidates: (scope: AssistantManagementScope & { query?: string }, signal?: AbortSignal) =>
    read<AssistantPage<{ member_id: number; name: string }> & { appointment_updated_at: string }>("candidates/", scope, signal),
  managed: (scope: AssistantManagementScope, signal?: AbortSignal) =>
    read<AssistantPage<AssistantAssignment> & { appointment_updated_at: string }>("managed/", scope, signal),
  mine: (scope: AssistantPageScope, signal?: AbortSignal) => read<AssistantPage<AssistantInvitation>>("mine/", scope, signal),
  invite: (payload: { business_id: number; patient_id: number; appointment_id: number; target_member_id: number; expected_updated_at: string }, key: string, signal?: AbortSignal) =>
    command<AssistantCommandResult>("", payload, key, signal),
  accept: (id: number, payload: { business_id: number; expected_revision: number }, key: string, signal?: AbortSignal) =>
    command<AssistantCommandResult>(`${id}/accept/`, payload, key, signal),
  revoke: (id: number, payload: { business_id: number; expected_revision: number }, key: string, signal?: AbortSignal) =>
    command<AssistantCommandResult>(`${id}/revoke/`, payload, key, signal),
  workspace: (id: number, businessId: number, signal?: AbortSignal) =>
    read<AssistantWorkspace>(`${id}/workspace/`, { business_id: businessId }, signal),
  drafts: (id: number, scope: AssistantPageScope, signal?: AbortSignal) =>
    read<AssistantPage<AssistantDraftRow>>(`${id}/drafts/`, scope, signal),
  templates: (id: number, scope: AssistantPageScope, signal?: AbortSignal) =>
    read<AssistantPage<AssistantTemplateRow>>(`${id}/templates/`, scope, signal),
  document: (id: number, scope: AssistantDocumentScope & { document_id: number }, signal?: AbortSignal) =>
    read<DocumentVersion>(`${id}/document/`, scope, signal),
  preview: (id: number, scope: AssistantDocumentScope & { template_version_id: number; document_id?: number }, signal?: AbortSignal) =>
    read<DocumentPreview>(`${id}/preview/`, scope, signal),
  saveDocument: (id: number, payload: AssistantDocumentDraft, key: string, signal?: AbortSignal) =>
    command<{ id: number; version_id: number; revision: number; replayed: boolean }>(`${id}/save-document/`, payload, key, signal),
};
