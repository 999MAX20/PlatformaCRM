import { apiClient } from "./client";

export type RuleMoment = "optional" | "before_treatment" | "before_completion" | "before_issue";
export type RuleReviewer = "primary_clinician" | "medical_head";
export type RuleSigner = RuleReviewer | "patient_or_representative";
export type DocumentRequirements = { required_at: RuleMoment; required_fields: string[];
  reviewers: RuleReviewer[]; signers: RuleSigner[]; issuable: boolean };
export type CapturedDocumentRules = { business_id: number; kind_id: number; version_id: number; revision: number;
  name: string; validation: "synthetic"; docx_allowed: boolean; service_id: number; rule: DocumentRequirements };
export type DocumentRuleContent = { name: string; docx_allowed: boolean; validation: "synthetic";
  default: DocumentRequirements; services: { id: number; name: string; rule: DocumentRequirements }[];
  templates: { id: number; title: string }[] };
export type DocumentRuleVersion = { schema: 1; business_id: number; kind_id: number; version_id: number;
  revision: number; author_id: number; created_at: string; content: DocumentRuleContent; reason: string };
export type DocumentRuleAccess = { business_id: number; actions: { view: boolean; save: boolean };
  validation: "synthetic"; fields: string[]; moments: RuleMoment[]; reviewers: RuleReviewer[]; signers: RuleSigner[] };
export type DocumentRuleDraft = { business_id: number; expected_revision?: number; reason: string; template_ids: number[];
  content: Pick<DocumentRuleContent, "name" | "docx_allowed" | "default"> & {
    services: { service_id: number; rule: DocumentRequirements }[] } };
type Page = { results: DocumentRuleVersion[]; next_before_id: number | null };
const root = "/api/medical/document-kinds/";
async function read<T>(path: string, params: object, signal?: AbortSignal) {
  return (await apiClient.get<T>(root + path, { params, signal })).data;
}
export const medicalDocumentRulesApi = {
  access: (business_id: number, signal?: AbortSignal) => read<DocumentRuleAccess>("workspace-access/", { business_id }, signal),
  list: (business_id: number, q: string, before_id?: number, signal?: AbortSignal) => read<Page>("", { business_id, q, before_id }, signal),
  version: (business_id: number, version_id: number, signal?: AbortSignal) => read<DocumentRuleVersion>(`versions/${version_id}/`, { business_id }, signal),
  history: (business_id: number, kind_id: number, before_id?: number, signal?: AbortSignal) =>
    read<Page & { kind_id: number; current_revision: number }>(`${kind_id}/history/`, { business_id, before_id }, signal),
  save: async (kind_id: number | null, payload: DocumentRuleDraft, key: string, signal?: AbortSignal) =>
    (await apiClient.post<{ kind_id: number; version_id: number; revision: number; replayed: boolean }>(
      root + (kind_id === null ? "" : `${kind_id}/save/`), payload, { headers: { "Idempotency-Key": key }, signal })).data,
};
