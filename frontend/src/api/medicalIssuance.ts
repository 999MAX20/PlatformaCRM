import axios from "axios";
import { apiClient } from "./client";

export type IssuanceScope = { business_id: number; patient_id: number; branch_id: number };
export type DocumentGrant = { id: number; state: "pending" | "active" | "revoked" | "expired"; revision: number;
  encounter_id: number; representative_id: number | null; activated_at: string | null; expires_at: string | null;
  created_at: string; version_ids: number[]; notification_status: string };
export type IssuanceWorkspace = { patient_id: number; business_slug: string; synthetic: boolean;
  encounters: Array<{ id: number; started_at: string }>; next_before_id: number | null;
  next_before_version_id: number | null; next_before_grant_id: number | null;
  versions: Array<{ id: number; revision: number; title: string; finalized: boolean }>;
  representatives: Array<{ id: number; name: string }>; grants: DocumentGrant[] };
export type GrantCreate = IssuanceScope & { encounter_id: number; version_ids: number[]; personally_verified: boolean;
  verification_reason: string; representative_id?: number; replaces_id?: number };
export type GrantResult = { grant: DocumentGrant; code?: string | null; replayed: boolean };
const grants = "/api/medical/document-grants/";
export const medicalIssuanceApi = {
  byClient: async (params: { business_id: number; branch_id: number; client_id: number }, signal?: AbortSignal) =>
    (await apiClient.get<IssuanceWorkspace>(`${grants}by-client/`, { params, signal })).data,
  workspace: async (params: IssuanceScope & { encounter_id?: number; before_id?: number; before_version_id?: number; before_grant_id?: number }, signal?: AbortSignal) =>
    (await apiClient.get<IssuanceWorkspace>(grants, { params, signal })).data,
  create: async (payload: GrantCreate, key: string, signal?: AbortSignal) =>
    (await apiClient.post<GrantResult>(grants, payload, { headers: { "Idempotency-Key": key }, signal })).data,
  transition: async (id: number, payload: IssuanceScope & { expected_revision: number; action: "activate" | "revoke"; reason: string }, key: string, signal?: AbortSignal) =>
    (await apiClient.post<GrantResult>(`${grants}${id}/transition/`, payload, { headers: { "Idempotency-Key": key }, signal })).data,
};

export type PortalDocuments = { expires_at: string; session_expires_at: string; synthetic: boolean;
  documents: Array<{ id: string; title: string; revision: number; has_correction: boolean }> };
const baseURL = import.meta.env.VITE_API_URL || "";
const publicClient = axios.create({ baseURL, withCredentials: true, timeout: 20_000 });
const portalPath = (slug: string) => `/api/medical/portal/${encodeURIComponent(slug)}/`;
async function csrf(signal?: AbortSignal) {
  const { data } = await publicClient.get<{ csrf_token: string }>("/api/auth/csrf/", { signal });
  if (!data.csrf_token) throw new Error("Missing CSRF token");
  return { signal, headers: { "X-CSRFToken": data.csrf_token } };
}
export const medicalPortalApi = {
  login: async (slug: string, code: string, signal?: AbortSignal) =>
    publicClient.post(portalPath(slug), { code }, await csrf(signal)),
  documents: async (slug: string, signal?: AbortSignal) =>
    (await publicClient.get<PortalDocuments>(portalPath(slug), { signal })).data,
  archive: async (slug: string, signal?: AbortSignal) =>
    (await publicClient.get<Blob>(`${portalPath(slug)}archive/`, { signal, responseType: "blob" })).data,
  logout: async (slug: string, signal?: AbortSignal) => publicClient.delete(portalPath(slug), await csrf(signal)),
  fileUrl: (slug: string, id: string, download = false) => `${baseURL}${portalPath(slug)}files/${encodeURIComponent(id)}/${download ? "?download=1" : ""}`,
};
