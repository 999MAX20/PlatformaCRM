import { apiClient } from "./client";
import type { ClinicalReadScope, ClinicalContent } from "./medicalClinical";
import type { TemplateVersion } from "./medicalTemplates";
import type { CapturedDocumentRules } from "./medicalDocumentRules";

export type DocumentScope = ClinicalReadScope & { encounter_id: number };
export type HeadDocumentScope = { business_id: number; patient_id: number; head_branch_id: number; encounter_id?: never };
export type DocumentReadScope = ClinicalReadScope | HeadDocumentScope;
export type DocumentAccess = { patient_revision: number; encounter_revision: number;
  actions: { view: boolean; create: boolean; update: boolean } };
export type DocumentPreview = { document_text: string; template: TemplateVersion;
  patient_revision: number; encounter_revision: number; source_digest: string;
  missing_fields: string[]; unknown_fields: string[]; available_fields: string[] };
export type DocumentRow = { document_id: number; version_id: number; revision: number;
  encounter_id: number; state: string; created_at: string; title: string };
export type DocumentRevision = { version_id: number; revision: number; author_id: number; created_at: string };
export type DocumentReview = { document_state: "draft" | "ready_for_review" | "reviewed"; state_revision: number;
  can_transition: boolean; next_before_id: number | null; results: { id: number; state: "draft" | "ready_for_review" | "reviewed";
    state_revision: number; actor: { id: number; name: string }; created_at: string; reason: string }[] };
export type DocumentReviewCommand = ClinicalReadScope & { expected_state_revision: number;
  target: "draft" | "ready_for_review" | "reviewed"; reason: string };
export type DocumentVersion = Omit<DocumentRow, "encounter_id" | "title"> & { snapshot: {
  document_rules?: CapturedDocumentRules | null;
  template: TemplateVersion["template"]; document_text?: string; clinical: ClinicalContent; reason: string;
  template_source?: { template_id: number; version_id: number; revision: number; approved_by: number; approved_at: string; review_id: number };
  prepared_by: { name: string; member_id: number; user_id: number };
  performed_by: { name: string; member_id: number; user_id: number };
} };
export type DocumentDraft = { business_id: number; patient_id: number; encounter_id: number;
  expected_encounter_revision: number; expected_patient_revision: number; template_version_id: number;
  document_text: string; reason: string; participation_id?: number; expected_source_digest?: string };
const root = "/api/medical/documents/";
async function read<T>(path: string, params: object, signal?: AbortSignal) {
  return (await apiClient.get<T>(root + path, { params, signal })).data;
}
async function save(path: string, payload: DocumentDraft & { expected_document_revision?: number }, key: string) {
  if (!key.trim() || key.length > 128) throw new Error("Medical command requires an idempotency key of at most 128 characters.");
  return (await apiClient.post<{ id: number; version_id: number; revision: number; replayed: boolean }>(root + path, payload,
    { headers: { "Idempotency-Key": key } })).data;
}
export const medicalDocumentsApi = {
  review: (scope: DocumentReadScope, id: number, before_id?: number, signal?: AbortSignal) =>
    read<DocumentReview>(`versions/${id}/review/`, { ...scope, before_id }, signal),
  transition: async (id: number, payload: DocumentReviewCommand, key: string) => {
    if (!key.trim() || key.length > 128) throw new Error("Medical command requires an idempotency key of at most 128 characters.");
    return (await apiClient.post<{ id: number; version_id: number; state: string; state_revision: number; replayed: boolean }>(
      root + `versions/${id}/review-transition/`, payload, { headers: { "Idempotency-Key": key } })).data;
  },
  access: (scope: DocumentScope, signal?: AbortSignal) => read<DocumentAccess>("workspace-access/", scope, signal),
  preview: (scope: DocumentScope, template_version_id: number, document_id?: number, signal?: AbortSignal) =>
    read<DocumentPreview>("preview/", { ...scope, template_version_id, document_id }, signal),
  list: (scope: DocumentScope | HeadDocumentScope, before_id?: number, signal?: AbortSignal) =>
    read<{ results: DocumentRow[]; next_before_id: number | null }>("", { ...scope, before_id }, signal),
  version: (scope: DocumentReadScope, id: number, signal?: AbortSignal) => read<DocumentVersion>(`versions/${id}/`, scope, signal),
  history: (scope: DocumentReadScope, id: number, before_revision?: number, signal?: AbortSignal) =>
    read<{ results: DocumentRevision[]; current_revision: number; next_before_revision: number | null }>(`${id}/revisions/`, { ...scope, before_revision }, signal),
  create: (payload: DocumentDraft, key: string) => save("", payload, key),
  update: (id: number, payload: DocumentDraft & { expected_document_revision: number }, key: string) => save(`${id}/draft/`, payload, key),
};
