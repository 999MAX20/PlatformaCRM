import { apiClient } from "./client";

export type ReceptionState = "new" | "pending" | "booked" | "declined" | "expired" | "cancelled";
export type ReceptionPageScope = { business_id: number; offset?: number; limit?: number };
export type FollowUpScope = ReceptionPageScope & { patient_id: number; encounter_id: number; participation_id?: number };
export type ReceptionRequest = {
  id: number; patient_id: number; client_id: number; client_name: string; branch_id: number;
  source_appointment_id: number; service_id: number; service_name: string;
  preferred_resource_id: number; preferred_resource_name: string; referring_clinician_name: string;
  assignee_id: number | null; assignee_name: string | null; assigned_to_me: boolean;
  created_at: string; recommended_from: string; recommended_until: string; duration_minutes: number | null;
  patient_in_clinic: boolean; acceptance_due_at: string | null; overdue: boolean;
  contact_cycle: number; contact_due_at: string | null; contact_attempts: number; closure_reason: string;
  state: ReceptionState; revision: number; booked_appointment_id: number | null;
  appointment_status: string | null; appointment_start_at: string | null;
  actions: { claim: boolean; book: boolean; link: boolean; transfer: boolean; contact: boolean; expire: boolean; reopen: boolean };
};
export type ReceptionPage = { results: ReceptionRequest[]; next_offset: number | null };
export type FollowUpOption = { id: number; name: string };
export type FollowUpOptions = { results: FollowUpOption[]; default: FollowUpOption | null; next_offset: number | null };
export type ReceptionCandidate = { id: number; start_at: string; end_at: string; updated_at: string; resource_name: string };
export type ReceptionCandidates = { results: ReceptionCandidate[]; next_offset: number | null };
export type ReceptionHistoryEntry = { id: number; created_at: string; kind: string; actor_name: string | null;
  from_name: string | null; to_name: string | null; reason: string; outcome?: string; cycle?: number };
export type ReceptionCommand = { business_id: number; expected_revision: number };
export type ReceptionResult = { id: number; state: ReceptionState; revision: number; replayed: boolean; appointment_id?: number };
export type FollowUpDraft = Omit<FollowUpScope, "offset" | "limit"> & {
  expected_revision: number; service_id: number; preferred_resource_id: number;
  recommended_from: string; recommended_until: string; patient_in_clinic: boolean; duration_minutes?: number | null;
};
export type ReceptionBooking = ReceptionCommand & {
  resource_id: number; start_at: string; expected_price: string | null;
  expected_duration_minutes: number; confirmed: true;
};

const root = "/api/reception/booking-requests/";
async function read(params: object, path = "", signal?: AbortSignal) {
  return (await apiClient.get<ReceptionPage>(root + path, { params, signal })).data;
}
async function command(path: string, payload: object, key: string, signal?: AbortSignal) {
  if (!key.trim() || key.length > 128) throw new Error("Medical command requires an idempotency key of at most 128 characters.");
  return (await apiClient.post<ReceptionResult>(root + path, payload, {
    headers: { "Idempotency-Key": key }, signal,
  })).data;
}

export const medicalReceptionApi = {
  contact: (id: number, payload: ReceptionCommand & { action: string; reason: string }, key: string, signal?: AbortSignal) =>
    command(`${id}/contact/`, payload, key, signal),
  recipients: async (id: number, scope: ReceptionPageScope & { search?: string }, signal?: AbortSignal) =>
    (await apiClient.get<{ results: FollowUpOption[]; next_offset: number | null }>(root + `${id}/recipients/`, { params: scope, signal })).data,
  history: async (id: number, scope: ReceptionPageScope, signal?: AbortSignal) =>
    (await apiClient.get<{ results: ReceptionHistoryEntry[]; next_offset: number | null }>(root + `${id}/history/`, { params: scope, signal })).data,
  transfer: (id: number, payload: ReceptionCommand & { assignee_id: number | null; reason: string }, key: string, signal?: AbortSignal) =>
    command(`${id}/transfer/`, payload, key, signal),
  candidates: async (id: number, scope: ReceptionPageScope, signal?: AbortSignal) =>
    (await apiClient.get<ReceptionCandidates>(root + `${id}/candidates/`, { params: scope, signal })).data,
  catalog: async (scope: FollowUpScope & { kind: "service" | "staff"; search?: string }, signal?: AbortSignal) =>
    (await apiClient.get<FollowUpOptions>(root + "catalog/", { params: scope, signal })).data,
  queue: (scope: ReceptionPageScope & { branch_id: number; state?: ReceptionState; request_id?: number }, signal?: AbortSignal) =>
    read(scope, "", signal),
  primary: (scope: FollowUpScope, signal?: AbortSignal) => read(scope, "primary/", signal),
  create: (payload: FollowUpDraft, key: string, signal?: AbortSignal) => command("", payload, key, signal),
  claim: (id: number, payload: ReceptionCommand, key: string, signal?: AbortSignal) =>
    command(`${id}/claim/`, payload, key, signal),
  book: (id: number, payload: ReceptionBooking, key: string, signal?: AbortSignal) =>
    command(`${id}/book/`, payload, key, signal),
  link: (id: number, payload: ReceptionCommand & { appointment_id: number; expected_updated_at: string; confirmed: true }, key: string, signal?: AbortSignal) =>
    command(`${id}/link/`, payload, key, signal),
};
