import { apiClient } from "./client";
import type { Id } from "../types";

export const importEntities = ["clients", "services", "specialists", "appointments"] as const;
export type ImportEntity = typeof importEntities[number];
export type ImportField = {
  key: string; label: string; field_type: "text" | "number" | "date" | "boolean" | "select";
  options: string[]; definition_id?: number; in_card: boolean; in_table: boolean; in_filters: boolean; in_calendar?: boolean;
};
export type ImportDecision = { action: "create" | "fill" | "update" | "skip"; target_id?: number; update_fields?: string[] };
export type ImportSource = {
  id: number; filename: string; sheet_name: string; entity_type: ImportEntity; total_rows: number;
  headers: string[]; mapping: Record<string, string>; fields: ImportField[]; columns: string[];
  resolutions: Record<string, ImportDecision>; corrections: Record<string, Record<string, string>>; excluded: number[];
  suggested_mapping: Record<ImportEntity, Record<string, string>>; suggested_types: Record<string, ImportField["field_type"]>;
};
export type ImportSourceRow = { row: number; original: Record<string, string>; values: Record<string, string>; excluded: boolean };
export type ImportReportRow = {
  source_id: number; row: number; entity_type: ImportEntity; reference: string; id?: number; existing_id?: number;
  outcome: "created" | "updated" | "unchanged" | "skipped"; values: Record<string, unknown>;
  before?: Record<string, unknown>; before_custom?: Record<string, { value?: unknown }>;
  custom: Record<string, { value?: unknown }>; before_version?: string | null;
};
export type ImportReport = {
  ready?: boolean; access_changed?: boolean; rows?: ImportReportRow[];
  errors?: { source_id: number; row: number; entity_type: ImportEntity; reference: string; values: Record<string, unknown>; errors: unknown }[];
  summary?: Record<ImportReportRow["outcome"], number>;
};
export type ImportWorkspaceSummary = {
  id: number; business: Id; state: "draft" | "ready" | "imported" | "cancelled";
  operation: { id?: string; action?: "preview" | "confirm"; status?: "pending" | "running" | "succeeded" | "failed"; error?: string; total_rows?: number };
  version: number; validated_version: number | null; created_at: string; updated_at: string;
};
export type ImportWorkspace = ImportWorkspaceSummary & {
  sources: ImportSource[]; report: ImportReport; result: ImportReport; mapping_fields: Record<ImportEntity, string[]>;
};
export type ImportProfile = { id: number; name: string; entity_type: ImportEntity };
export type ImportActivation = { token: string; records: { id: number; start_at: string; client_name: string; service_name: string; specialist_name: string }[] };
const root = "/api/import-workspaces/";
async function command(id: number, action: string, payload: unknown) {
  return (await apiClient.post<ImportWorkspace>(`${root}${id}/${action}/`, payload)).data;
}
export const importWorkspaceApi = {
  profiles: async (id: number) => (await apiClient.get<{ results: ImportProfile[] }>(`${root}${id}/profiles/`)).data,
  saveProfile: (id: number, version: number, source_id: number, name: string) => command(id, "save_profile", { version, source_id, name }),
  applyProfile: (id: number, version: number, source_id: number, profile_id: number) => command(id, "apply_profile", { version, source_id, profile_id }),
  activation: async (id: number) => (await apiClient.get<ImportActivation>(`${root}${id}/activation/`)).data,
  activate: async (id: number, token: string, ids: number[]) => (await apiClient.post<{ activated: number[] }>(`${root}${id}/activate/`, { token, ids, confirmed: true })).data,
  list: async (business: Id, page = 1) => (await apiClient.get<{ count: number; results: ImportWorkspaceSummary[] }>(root, { params: { business, page } })).data,
  get: async (id: number) => (await apiClient.get<ImportWorkspace>(`${root}${id}/`)).data,
  create: async (business: Id) => (await apiClient.post<ImportWorkspace>(root, { business })).data,
  upload: async (id: number, version: number, file: File, entity_type: ImportEntity) => {
    const form = new FormData();
    form.append("version", String(version)); form.append("entity_type", entity_type); form.append("file", file);
    return (await apiClient.post<ImportWorkspace>(`${root}${id}/upload/`, form, { headers: { "Content-Type": "multipart/form-data" } })).data;
  },
  configure: (id: number, version: number, source: ImportSource) => command(id, "configure", {
    version, source_id: source.id, entity_type: source.entity_type, mapping: source.mapping,
    fields: source.fields, columns: source.columns, resolutions: source.resolutions,
  }),
  saveSource: (id: number, version: number, source: ImportSource) => command(id, "save_source", {
    version, source_id: source.id, entity_type: source.entity_type, mapping: source.mapping,
    fields: source.fields, columns: source.columns, resolutions: source.resolutions,
    corrections: source.corrections, excluded: source.excluded,
  }),
  correct: (id: number, version: number, source: ImportSource) => command(id, "correct", {
    version, source_id: source.id, corrections: source.corrections, excluded: source.excluded,
  }),
  removeSource: (id: number, version: number, source_id: number) => command(id, "remove_source", { version, source_id }),
  duplicate: (id: number, version: number, source_id: number, entity_type: ImportEntity) => command(id, "duplicate_source", { version, source_id, entity_type }),
  rows: async (id: number, source_id: number, page: number) => (await apiClient.get<{ count: number; version: number; results: ImportSourceRow[] }>(`${root}${id}/rows/`, { params: { source_id, page } })).data,
  candidates: async (id: number, entity_type: ImportEntity, search: string) => (await apiClient.get<{ results: { id: number; label: string }[] }>(`${root}${id}/candidates/`, { params: { entity_type, search } })).data,
  references: async (id: number, entity_type: ImportEntity, params: { search?: string; page?: number; reference?: string }) => (await apiClient.get<{ count: number; results: { reference: string; label: string }[] }>(`${root}${id}/references/`, { params: { entity_type, ...params } })).data,
  preview: (id: number, version: number) => command(id, "preview", { version, background: true }),
  confirm: (id: number, version: number) => command(id, "confirm", { version, background: true }),
  cancel: (id: number, version: number) => command(id, "cancel", { version }),
};
