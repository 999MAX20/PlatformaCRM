import { apiClient } from "./client";

export type PatientScope = { business_id: number; branch_id: number };
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
