import axios from "axios";
import { apiClient } from "./client";

type FileBasis =
  | { appointment_id: number; participation_id?: never; correction_access_id?: never; head_branch_id?: never }
  | { participation_id: number; appointment_id?: never; correction_access_id?: never; head_branch_id?: never }
  | { correction_access_id: number; appointment_id?: never; participation_id?: never; head_branch_id?: never }
  | { head_branch_id: number; appointment_id?: never; participation_id?: never; correction_access_id?: never };
export type MedicalFileScope = { business_id: number; patient_id: number } & FileBasis;
export type MedicalFileWorkspaceScope = MedicalFileScope & { record_id?: number; encounter_id?: number };
export type MedicalFileAccess = { patient_revision: number; actor_id: number;
  record_id: number | null; encounter_id: number | null;
  actions: { upload: boolean; export: boolean }; allowed_extensions: string[]; max_bytes: number };
export type MedicalFileVersion = {
  id: number; version_id: number; revision: number; record_id: number; encounter_id: number | null;
  branch_id: number; branch_name: string; author_name: string; created_at: string;
  name: string; description: string; teeth: number[]; reason: string; size: number; content_type: string;
  scan_status: "pending" | "scanning" | "clean" | "infected" | "error";
  actions?: { edit_metadata: boolean };
};
export type MedicalFileCommand = { id: number; version_id: number; revision: number; replayed: boolean };
export type MedicalFileUpload = MedicalFileWorkspaceScope & { record_id: number; file: File; expected_patient_revision: number;
  description: string; teeth: number[]; reason?: string };
export type MedicalFileMetadata = MedicalFileScope & { expected_revision: number; description: string; teeth: number[]; reason: string };
export type MedicalFileFilter = { before_id?: number; limit?: number; tooth?: number; encounter_id?: number };
const root = "/api/medical/files/";

function readScope(scope: MedicalFileScope) {
  return { business_id: scope.business_id, patient_id: scope.patient_id, appointment_id: scope.appointment_id,
    participation_id: scope.participation_id, correction_access_id: scope.correction_access_id, head_branch_id: scope.head_branch_id };
}

async function read<T>(path: string, params: object, signal?: AbortSignal) {
  return (await apiClient.get<T>(root + path, { params, signal })).data;
}

function commandHeaders(key: string) {
  if (!key.trim() || key.length > 128) throw new Error("Medical command requires an idempotency key of at most 128 characters.");
  return { "Idempotency-Key": key };
}

async function readBlob(scope: MedicalFileScope, id: number, operation: "preview" | "download", versionId?: number, signal?: AbortSignal) {
  try {
    return (await apiClient.get<Blob>(`${root}${id}/${operation}/`, {
      params: { ...readScope(scope), version_id: versionId }, signal, responseType: "blob",
    })).data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.data instanceof Blob && error.response.data.size <= 65536 &&
        error.response.data.type.includes("json")) {
      try { error.response.data = JSON.parse(await error.response.data.text()); } catch { /* Preserve the original HTTP failure. */ }
    }
    throw error;
  }
}

export const medicalFilesApi = {
  access: (scope: MedicalFileWorkspaceScope, signal?: AbortSignal) => read<MedicalFileAccess>("workspace-access/", scope, signal),
  list: (scope: MedicalFileScope, filter: MedicalFileFilter = {}, signal?: AbortSignal) =>
    read<{ results: MedicalFileVersion[]; next_before_id: number | null }>("", { ...readScope(scope), ...filter }, signal),
  version: (scope: MedicalFileScope, id: number, versionId?: number, signal?: AbortSignal) =>
    read<MedicalFileVersion>(`${id}/`, { ...readScope(scope), version_id: versionId }, signal),
  history: (scope: MedicalFileScope, id: number, beforeRevision?: number, signal?: AbortSignal) =>
    read<{ results: MedicalFileVersion[]; next_before_revision: number | null }>(`${id}/revisions/`,
      { ...readScope(scope), before_revision: beforeRevision }, signal),
  upload: async (payload: MedicalFileUpload, key: string, signal?: AbortSignal, onProgress?: (fraction: number) => void) => {
    const headers = { ...commandHeaders(key), "Content-Type": "multipart/form-data" };
    const form = new FormData();
    for (const [name, value] of Object.entries(payload)) {
      if (value === undefined) continue;
      if (name === "file") form.append(name, payload.file);
      else if (Array.isArray(value)) value.forEach(item => form.append(name, String(item)));
      else form.append(name, String(value));
    }
    return (await apiClient.post<MedicalFileCommand>(root, form, { headers, signal,
      onUploadProgress: event => { if (event.total) onProgress?.(Math.min(1, event.loaded / event.total)); },
    })).data;
  },
  updateMetadata: async (id: number, payload: MedicalFileMetadata, key: string, signal?: AbortSignal) =>
    (await apiClient.post<MedicalFileCommand>(`${root}${id}/metadata/`, { ...readScope(payload),
      expected_revision: payload.expected_revision, description: payload.description, teeth: payload.teeth, reason: payload.reason,
    }, { headers: commandHeaders(key), signal })).data,
  preview: (scope: MedicalFileScope, id: number, versionId?: number, signal?: AbortSignal) => readBlob(scope, id, "preview", versionId, signal),
  download: (scope: MedicalFileScope, id: number, versionId?: number, signal?: AbortSignal) => readBlob(scope, id, "download", versionId, signal),
};
