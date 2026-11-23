import { apiClient } from "./client";
import type { ClinicalReadScope } from "./medicalClinical";
import type { TemplateVersion } from "./medicalTemplates";

export type OrderTemplateSource = { template: TemplateVersion["template"]; source_digest: string;
  approval: { template_id: number; version_id: number; revision: number; review_id: number; approved_by: number; approved_at: string } };
export type OrderPreview = { document_text: string; missing_fields: string[]; unknown_fields: string[];
  template_source: OrderTemplateSource; patient_revision: number; encounter_revision: number };

export const orderKinds = ["medication", "imaging", "laboratory", "consultation", "hygiene", "follow_up", "other"] as const;
export const medicationFields = ["name", "dose", "route", "frequency", "duration"] as const;
export type OrderContent = { kind: typeof orderKinds[number]; text: string;
  medication: Partial<Record<typeof medicationFields[number], string>> };
export type OrderScope = ClinicalReadScope & { encounter_id: number };
export type OrderAccess = { patient_revision: number; encounter_revision: number; actor_id: number;
  actions: { view: boolean; create: boolean; update: boolean } };
export type OrderVersion = { order_id: number; version_id: number; revision: number; encounter_id: number;
  state: "draft"; author_id: number; author_name: string; created_at: string; content: OrderContent; reason: string; template_source?: OrderTemplateSource };
export type OrderDraft = { business_id: number; patient_id: number; encounter_id: number;
  expected_patient_revision: number; expected_encounter_revision: number; content: OrderContent; reason: string;
  participation_id?: number; expected_order_revision?: number; template_version_id?: number; expected_source_digest?: string };
const root = "/api/medical/orders/";
async function read<T>(path: string, params: object, signal?: AbortSignal) {
  return (await apiClient.get<T>(root + path, { params, signal })).data;
}
export const medicalOrdersApi = {
  preview: (scope: OrderScope, template_version_id: number, order_id?: number, signal?: AbortSignal) =>
    read<OrderPreview>("preview/", { ...scope, template_version_id, order_id }, signal),
  access: (scope: OrderScope, signal?: AbortSignal) => read<OrderAccess>("workspace-access/", scope, signal),
  list: (scope: OrderScope, before_id?: number, signal?: AbortSignal) =>
    read<{ results: OrderVersion[]; next_before_id: number | null }>("", { ...scope, before_id }, signal),
  history: (scope: ClinicalReadScope, id: number, before_revision?: number, signal?: AbortSignal) =>
    read<{ results: OrderVersion[]; current_revision: number; next_before_revision: number | null }>(`${id}/revisions/`, { ...scope, before_revision }, signal),
  save: async (id: number | null, payload: OrderDraft, key: string) => {
    if (!key.trim() || key.length > 128) throw new Error("Medical command requires an idempotency key of at most 128 characters.");
    return (await apiClient.post<{ id: number; version_id: number; revision: number; replayed: boolean }>(
      root + (id ? `${id}/draft/` : ""), payload, { headers: { "Idempotency-Key": key } })).data;
  },
};
