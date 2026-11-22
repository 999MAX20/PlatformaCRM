import { apiClient } from "./client";

export type TemplateAccess = { business_id: number; member_id: number; kind: "doctor" | "head";
  actions: { view: boolean; create: boolean; update: boolean } };
export type TemplateRow = { template_id: number; version_id: number; revision: number; title: string; created_at: string };
export type TemplateVersionRow = { version_id: number; revision: number; author_id: number; created_at: string };
export type TemplateVersion = TemplateVersionRow & { template_id: number; current_revision: number;
  template: { code: string; version: number; title: string; text: string }; reason: string };
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
export const medicalTemplatesApi = {
  access: (business_id: number, signal?: AbortSignal) => read<TemplateAccess>("workspace-access/", { business_id }, signal),
  list: (business_id: number, before_id?: number, signal?: AbortSignal) =>
    read<{ results: TemplateRow[]; next_before_id: number | null }>("", { business_id, before_id }, signal),
  history: (business_id: number, template_id: number, before_revision?: number, signal?: AbortSignal) =>
    read<{ results: TemplateVersionRow[]; current_revision: number; next_before_revision: number | null }>(`${template_id}/revisions/`, { business_id, before_revision }, signal),
  version: (business_id: number, version_id: number, signal?: AbortSignal) => read<TemplateVersion>(`versions/${version_id}/`, { business_id }, signal),
  create: (payload: TemplateDraft, key: string) => save("", payload, key),
  update: (template_id: number, payload: TemplateDraft & { expected_revision: number }, key: string) => save(`${template_id}/draft/`, payload, key),
};
