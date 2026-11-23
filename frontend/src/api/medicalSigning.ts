import { apiClient } from "./client";
import type { DocumentReadScope } from "./medicalDocuments";

export type SigningSession = { id: string; revision: number; state: "pending" | "completed" | "cancelled";
  adapter: string; artifact_id: number; events: { revision: number; action: string; signer: string;
    position: number | null; created_at: string; actor: { id: number; name: string } }[] };
export type SigningState = { synthetic_enabled: boolean; can_prepare: boolean; can_start: boolean;
  can_sign: boolean; can_cancel: boolean; next_signer: string | null;
  artifact: { id: number; scan_status: string; sha256: string } | null;
  prerequisites: { ready: boolean; blockers: string[]; signers: string[] }; current: SigningSession | null; history: SigningSession[] };
const root = (id: number) => `/api/medical/documents/versions/${id}/`;
export const medicalSigningApi = {
  pdf: async (scope: DocumentReadScope, id: number, artifact_id: number, signal?: AbortSignal) =>
    (await apiClient.get<Blob>(root(id) + "signing-pdf/", { params: { ...scope, artifact_id }, responseType: "blob", signal })).data,
  read: async (scope: DocumentReadScope, id: number, language: string, signal?: AbortSignal) =>
    (await apiClient.get<SigningState>(root(id) + "signing/", { params: { ...scope, language }, signal })).data,
  prepare: async (id: number, payload: DocumentReadScope & { language: string }) =>
    (await apiClient.post<{ artifact_id: number; scan_status: string }>(root(id) + "prepare-signing/", payload)).data,
  start: async (id: number, payload: DocumentReadScope & { artifact_id: number }, key: string) => {
    if (!key.trim() || key.length > 128) throw new Error("Invalid idempotency key");
    return (await apiClient.post<SigningSession>(root(id) + "start-signing/", payload, { headers: { "Idempotency-Key": key } })).data;
  },
  advance: async (id: number, payload: DocumentReadScope & { session_id: string; expected_revision: number; action: "sign" | "cancel" }, key: string) => {
    if (!key.trim() || key.length > 128) throw new Error("Invalid idempotency key");
    return (await apiClient.post<SigningSession>(root(id) + "advance-signing/", payload, { headers: { "Idempotency-Key": key } })).data;
  },
};
