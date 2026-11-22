import { apiClient } from "./client";

export type CredentialAccess = { business_id: number; member_id: number; kind: "doctor" | "head";
  actions: { view: boolean; confirm: boolean } };
export type CredentialSummary = { id: number; revision: number; author_id: number; created_at: string;
  confirmed_by_id: number | null; confirmed_at: string | null };
export type CredentialContent = { license: string } | { specialty: string; position: string; qualification: string };
export type CredentialVersion = CredentialSummary & { content: CredentialContent; reason: string };
export type CredentialProfile = { member_id: number | null; current_revision: number; version: CredentialVersion | null };
export type CredentialDraft = { business_id: number; member_id: number | null; expected_revision: number; content: CredentialContent; reason: string };
const root = "/api/medical/credentials/";
async function read<T>(path: string, params: object, signal?: AbortSignal) {
  return (await apiClient.get<T>(root + path, { params, signal })).data;
}
export const medicalCredentialsApi = {
  access: (business_id: number, signal?: AbortSignal) => read<CredentialAccess>("workspace-access/", { business_id }, signal),
  members: (business_id: number, before_id?: number, signal?: AbortSignal) =>
    read<{ results: { id: number; name: string }[]; next_before_id: number | null }>("members/", { business_id, before_id }, signal),
  profile: (business_id: number, member_id: number | null, version_id?: number, signal?: AbortSignal) =>
    read<CredentialProfile>("", { business_id, member_id: member_id ?? undefined, version_id }, signal),
  history: (business_id: number, member_id: number | null, before_revision?: number, signal?: AbortSignal) =>
    read<{ results: CredentialSummary[]; next_before_revision: number | null }>("revisions/", { business_id, member_id: member_id ?? undefined, before_revision }, signal),
  confirm: async (payload: CredentialDraft, key: string) => {
    if (!key.trim() || key.length > 128) throw new Error("Medical command requires an idempotency key of at most 128 characters.");
    return (await apiClient.post<{ version_id: number; revision: number; replayed: boolean }>(root, payload,
      { headers: { "Idempotency-Key": key } })).data;
  },
};
