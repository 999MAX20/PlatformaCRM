import { apiClient } from "./client";

export type TemplateAccess = { business_id: number; member_id: number; kind: "doctor" | "head";
  actions: { view: boolean; create: boolean; update: boolean; approve: boolean } };
export type TemplateReviewSummary = { state: "pending" | "approved" | "rejected"; submitted_at: string; decided_at: string | null; decision_reason: string };
export type TemplateRow = { template_id: number; version_id: number; revision: number; title: string; created_at: string };
export type TemplateVersionRow = { version_id: number; revision: number; author_id: number; created_at: string };
export type TemplateVersion = TemplateVersionRow & { template_id: number; current_revision: number;
  template: { code: string; version: number; title: string; text: string }; reason: string; review: TemplateReviewSummary | null };
export type TemplateReview = TemplateReviewSummary & Omit<TemplateVersion, "review" | "author_id" | "created_at">;
export type TemplateDraft = { business_id: number; title: string; text: string; reason: string };
export type TemplateResult = { id: number; version_id: number; revision: number; replayed: boolean };
const root = "/api/medical/document-templates/";
async function read<T>(path: string, params: object, signal?: AbortSignal) {
  return (await apiClient.get<T>(root + path, { params, signal })).data;
}
async function save(path: string, payload: TemplateDraft & { expected_revision?: number }, key: string) {
  if (!key.trim() || key.length > 128) throw new Error("Medical command requires an idempotency key of at most 128 characters.");
  return (await apiClient.post<TemplateResult>(root + path, payload, { headers: { "Idempotency-Key": key } })).data;
}
async function reviewCommand(path: string, payload: object, key: string) {
  if (!key.trim() || key.length > 128) throw new Error("Medical command requires an idempotency key of at most 128 characters.");
  return (await apiClient.post(root + path, payload, { headers: { "Idempotency-Key": key } })).data;
}
export const medicalTemplatesApi = {
  access: (business_id: number, signal?: AbortSignal) => read<TemplateAccess>("workspace-access/", { business_id }, signal),
  list: (business_id: number, before_id?: number, signal?: AbortSignal) =>
    read<{ results: TemplateRow[]; next_before_id: number | null }>("", { business_id, before_id }, signal),
  history: (business_id: number, template_id: number, before_revision?: number, signal?: AbortSignal) =>
    read<{ results: TemplateVersionRow[]; current_revision: number; next_before_revision: number | null }>(`${template_id}/revisions/`, { business_id, before_revision }, signal),
  version: (business_id: number, version_id: number, signal?: AbortSignal) => read<TemplateVersion>(`versions/${version_id}/`, { business_id }, signal),
  pending: (business_id: number, before_id?: number, signal?: AbortSignal) =>
    read<{ results: (Omit<TemplateRow, "created_at"> & { submitted_at: string })[]; next_before_id: number | null }>("pending-reviews/", { business_id, before_id }, signal),
  review: (business_id: number, version_id: number, signal?: AbortSignal) => read<TemplateReview>(`versions/${version_id}/review/`, { business_id }, signal),
  submit: (version_id: number, payload: { business_id: number }, key: string) => reviewCommand(`versions/${version_id}/submit/`, payload, key),
  decide: (version_id: number, payload: { business_id: number; decision: "approved" | "rejected"; reason: string }, key: string) => reviewCommand(`versions/${version_id}/decision/`, payload, key),
  create: (payload: TemplateDraft, key: string) => save("", payload, key),
  update: (template_id: number, payload: TemplateDraft & { expected_revision: number }, key: string) => save(`${template_id}/draft/`, payload, key),
};

export const commonTemplatesApi: typeof medicalTemplatesApi = {
  ...medicalTemplatesApi,
  access: (business_id, signal) => read<TemplateAccess>("common/workspace-access/", { business_id }, signal),
  list: (business_id, before_id, signal) => read("common/", { business_id, before_id }, signal),
  history: (business_id, template_id, before_revision, signal) => read(`common/${template_id}/revisions/`, { business_id, before_revision }, signal),
  version: (business_id, version_id, signal) => read(`common/versions/${version_id}/`, { business_id }, signal),
  submit: (version_id, payload, key) => reviewCommand(`common/versions/${version_id}/submit/`, payload, key),
  create: (payload, key) => save("common/", payload, key),
  update: (template_id, payload, key) => save(`common/${template_id}/draft/`, payload, key),
};
