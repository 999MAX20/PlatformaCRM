import { apiClient } from "./client";

export type PatientScope = { business_id: number; branch_id: number };
export type PatientSearchKind = "name" | "phone" | "email" | "birth" | "iin";
export type PatientSearchRequest = PatientScope & { kind: PatientSearchKind; query: string; include_archived: boolean; offset: number; limit: number };
export type PatientSearchResult = {
  client_id: number; patient_id: number | null; full_name: string; phone: string; email: string;
  date_of_birth: string | null; is_archived: boolean; identity_status: "verified" | "unverified" | null;
  match: "exact_confirmed" | "possible";
};
export type PatientSearchPage = { results: PatientSearchResult[]; next_offset: number | null };
export type PatientRegistration = PatientScope & { full_name: string; phone: string; email: string; demographics: PatientDemographics;
  iin: string | null; confirmed_separate_person: boolean };
export type IdentityCorrection = { id: number; patient_id: number; state: "pending" | "applied" | "rejected";
  source_revision: number; applied_revision: number | null; medical_review_required: boolean;
  requested_by: string; created_at: string; proposed_iin: string | null; reason: string;
  decided_by: string | null; decided_at: string | null; decision_reason: string | null };
export type IdentityCorrectionsPage = { current_iin: string | null; results: IdentityCorrection[]; next_offset: number | null; actions: { approve: boolean } };
export type IdentityCorrectionResult = Pick<IdentityCorrection, "id" | "patient_id" | "state" | "applied_revision"> & { replayed: boolean };
export type PatientDemographics = { date_of_birth?: string; sex?: string; address?: string };
export type PatientProtocolLabel = Record<"ru" | "kk" | "en", string>;
export type PatientVerificationForm = {
  reference: string;
  methods: Array<{
    code: string;
    label: PatientProtocolLabel;
    fields: Array<{ code: string; label: PatientProtocolLabel; required: boolean; max_length: number }>;
  }>;
};
export type PatientAdministrationAccess = PatientScope & {
  actions: Record<"view" | "create" | "update" | "approve", boolean>;
};
export type PatientAdministration = {
  id: number;
  business_id: number;
  client_id: number;
  full_name: string;
  phone: string;
  email: string;
  demographics: PatientDemographics;
  iin: string | null;
  identity_status: "unverified" | "verified";
  revision: number;
  client_updated_at: string;
  verified_at: string | null;
};
export type PatientCommandResult = Pick<PatientAdministration, "id" | "client_id" | "revision" | "identity_status"> & {
  replayed: boolean;
};
export type PatientCreate = PatientScope & {
  client_id: number;
  demographics: PatientDemographics;
  iin?: string | null;
};
export type PatientPreliminaryUpdate = PatientScope & {
  expected_revision: number;
  demographics: PatientDemographics;
  iin: string | null;
  reason: string;
};
export type PatientVerification = PatientScope & {
  expected_revision: number;
  expected_client_updated_at: string;
  protocol_reference: string;
  method: string;
  fields: Record<string, string>;
};
export type PatientCorrection = PatientVerification & {
  full_name: string;
  demographics: PatientDemographics;
  reason: string;
};

const root = "/api/medical/patients/";

async function command(
  path: string,
  payload: PatientCreate | PatientPreliminaryUpdate | PatientVerification | PatientCorrection,
  idempotencyKey: string,
  signal?: AbortSignal,
) {
  if (!idempotencyKey.trim()) throw new Error("Patient command requires an idempotency key.");
  const { data } = await apiClient.post<PatientCommandResult>(root + path, payload, {
    headers: { "Idempotency-Key": idempotencyKey },
    signal,
  });
  return data;
}

export const medicalPatientsApi = {
  register: async (payload: PatientRegistration, key: string, signal?: AbortSignal) => {
    const { data } = await apiClient.post<PatientCommandResult>(root + "register/", payload, { headers: { "Idempotency-Key": key }, signal });
    return data;
  },
  identityCorrections: async (scope: PatientScope, clientId: number, offset = 0, signal?: AbortSignal) => {
    const { data } = await apiClient.get<IdentityCorrectionsPage>(root + "identity-corrections/", { params: { ...scope, client_id: clientId, offset }, signal });
    return data;
  },
  correctIin: async (patientId: number, payload: PatientVerification & { iin: string | null; reason: string }, key: string, signal?: AbortSignal) => {
    const { data } = await apiClient.post<IdentityCorrectionResult>(`${root}${patientId}/iin-correction/`, payload, { headers: { "Idempotency-Key": key }, signal });
    return data;
  },
  decideIdentityCorrection: async (correctionId: number, payload: { business_id: number; approve: boolean; reason: string }, key: string) => {
    const { data } = await apiClient.post<IdentityCorrectionResult>(`${root}identity-corrections/${correctionId}/decision/`, payload, { headers: { "Idempotency-Key": key } });
    return data;
  },
  searchAccess: async (businessId: number, signal?: AbortSignal) => {
    const { data } = await apiClient.get<{ business_id: number; branches: Array<{ id: number; name: string }>; actions: { create: boolean } }>(root + "search-access/", { params: { business_id: businessId }, signal });
    return data;
  },
  resolve: async (payload: PatientSearchRequest, signal?: AbortSignal) => {
    const { data } = await apiClient.post<PatientSearchPage>(root + "resolve/", payload, { signal });
    return data;
  },
  verificationForm: async (scope: PatientScope, signal?: AbortSignal) => {
    const { data } = await apiClient.get<PatientVerificationForm>(root + "verification-form/", { params: scope, signal });
    return data;
  },
  access: async (scope: PatientScope, signal?: AbortSignal) => {
    const { data } = await apiClient.get<PatientAdministrationAccess>(root + "access/", { params: scope, signal });
    return data;
  },
  byClient: async (clientId: number, scope: PatientScope, signal?: AbortSignal) => {
    const { data } = await apiClient.get<PatientAdministration>(`${root}by-client/${clientId}/`, { params: scope, signal });
    return data;
  },
  create: (payload: PatientCreate, idempotencyKey: string, signal?: AbortSignal) =>
    command("", payload, idempotencyKey, signal),
  preliminary: (patientId: number, payload: PatientPreliminaryUpdate, idempotencyKey: string, signal?: AbortSignal) =>
    command(`${patientId}/preliminary/`, payload, idempotencyKey, signal),
  verify: (patientId: number, payload: PatientVerification, idempotencyKey: string, signal?: AbortSignal) =>
    command(`${patientId}/verify/`, payload, idempotencyKey, signal),
  correct: (patientId: number, payload: PatientCorrection, idempotencyKey: string, signal?: AbortSignal) =>
    command(`${patientId}/correct/`, payload, idempotencyKey, signal),
};
