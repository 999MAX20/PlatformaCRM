import axios from "axios";
import { apiClient } from "./client";

type DocumentBasis =
  | { appointment_id: number; participation_id?: never; correction_access_id?: never; head_branch_id?: never }
  | { participation_id: number; appointment_id?: never; correction_access_id?: never; head_branch_id?: never }
  | { correction_access_id: number; appointment_id?: never; participation_id?: never; head_branch_id?: never }
  | { head_branch_id: number; appointment_id?: never; participation_id?: never; correction_access_id?: never };
export type DocumentArtifactScope = { business_id: number; patient_id: number } & DocumentBasis;
export type DocumentArtifact = { artifact_id: number; version_id: number; language: string;
  scan_status: "pending" | "scanning" | "clean" | "infected" | "error"; replayed: boolean; can_export: boolean; can_docx: boolean };
export type DocumentFieldRequirements = { version_id: number; revision: number; current: boolean;
  document_state: string; state_revision: number; configured: boolean; fields_complete: boolean;
  rule_version_id: number | null; fields: { field: string; present: boolean }[] };
export type DocumentExportEvent = { id: number; action: "document_exported" | "document_print_requested";
  created_at: string; actor: { id: number; name: string }; version_id: number; revision: number };
export type DocumentExportHistory = { results: DocumentExportEvent[]; next_before_id: number | null };

function params(scope: DocumentArtifactScope, language?: string) {
  return { business_id: scope.business_id, patient_id: scope.patient_id, appointment_id: scope.appointment_id,
    participation_id: scope.participation_id, correction_access_id: scope.correction_access_id,
    head_branch_id: scope.head_branch_id, language };
}
const root = "/api/medical/documents/versions/";
export async function blobResponse(request: Promise<{ data: Blob }>) {
  try { return (await request).data; }
  catch (error) {
    if (axios.isAxiosError(error) && error.response?.data instanceof Blob && error.response.data.size <= 65536 &&
        error.response.data.type.includes("json")) {
      try { error.response.data = JSON.parse(await error.response.data.text()); } catch { /* Preserve the HTTP failure. */ }
    }
    throw error;
  }
}
export const medicalDocumentArtifactsApi = {
  requirements: async (scope: DocumentArtifactScope, versionId: number, signal?: AbortSignal) =>
    (await apiClient.get<DocumentFieldRequirements>(`${root}${versionId}/requirements/`, { params: params(scope), signal })).data,
  prepareDocx: async (scope: DocumentArtifactScope, versionId: number, language: string, signal?: AbortSignal) =>
    (await apiClient.post<DocumentArtifact>(`${root}${versionId}/docx-prepare/`, params(scope, language), { signal })).data,
  downloadDocx: (scope: DocumentArtifactScope, versionId: number, language: string, signal?: AbortSignal) =>
    blobResponse(apiClient.post<Blob>(`${root}${versionId}/docx-download/`, params(scope, language), { signal, responseType: "blob" })),
  history: async (scope: DocumentArtifactScope, versionId: number, beforeId?: number, signal?: AbortSignal) =>
    (await apiClient.get<DocumentExportHistory>(`${root}${versionId}/export-history/`, {
      params: { ...params(scope), before_id: beforeId }, signal,
    })).data,
  prepare: async (scope: DocumentArtifactScope, versionId: number, language: string, signal?: AbortSignal) =>
    (await apiClient.post<DocumentArtifact>(`${root}${versionId}/pdf-prepare/`, params(scope, language), { signal })).data,
  preview: (scope: DocumentArtifactScope, versionId: number, language: string, signal?: AbortSignal) =>
    blobResponse(apiClient.get<Blob>(`${root}${versionId}/pdf/`, {
        params: params(scope, language), signal, responseType: "blob",
    })),
  export: (scope: DocumentArtifactScope, versionId: number, language: string, purpose: "download" | "print", signal?: AbortSignal) =>
    blobResponse(apiClient.post<Blob>(`${root}${versionId}/pdf-${purpose}/`, params(scope, language), { signal, responseType: "blob" })),
};
